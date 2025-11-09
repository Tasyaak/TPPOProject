import argparse, sqlite3, time, json, pathlib, random
import pandas as pd, numpy as np
from importlib import import_module
from joblib import dump
from sklearn.model_selection import StratifiedKFold, GridSearchCV, cross_validate
from sklearn.feature_extraction.text import TfidfVectorizer, HashingVectorizer
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, log_loss
from tensorflow import keras
from tensorflow.keras import layers


# ---- утилиты
def load_yaml(path): ...
def ts(): return time.strftime("%Y%m%d-%H%M%S")

def make_vectorizer(cfg):
    if cfg["features"]["use_hashing"]:
        hv = cfg["features"]["hashing"]
        return HashingVectorizer(n_features=hv["n_features"],
                                 alternate_sign=hv["alternate_sign"],
                                 ngram_range=tuple(hv["ngram_range"]),
                                 lowercase=False)
    else:
        tf = cfg["features"]["tfidf"]
        return TfidfVectorizer(max_features=tf["max_features"],
                               ngram_range=tuple(tf["ngram_range"]),
                               lowercase=tf["lowercase"])

def import_by_name(qualified):
    # "sklearn.linear_model.LogisticRegression" -> класс
    mod, cls = qualified.rsplit(".", 1)
    return getattr(import_module(mod), cls)

def build_keras_mlp(input_dim, p):
    model = keras.Sequential([
        layers.Input(shape=(input_dim,)),
        layers.Dense(p["hidden_units"], activation="relu"),
        layers.Dropout(p["dropout"]),
        layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer=keras.optimizers.Adam(p["lr"]),
                  loss="binary_crossentropy",
                  metrics=["accuracy"])
    return model

# ---- основной поток
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--only", default="")   # подмножество моделей через запятую
    args = ap.parse_args()
    cfg = load_yaml(args.config)
    random.seed(cfg["seed"]); np.random.seed(cfg["seed"])

    # 1) Читаем данные
    conn = sqlite3.connect(cfg["data"]["db_path"])
    df = pd.read_sql(cfg["data"]["sql_train"], conn)
    idc, txtc, yc = cfg["data"]["id_col"], cfg["data"]["text_col"], cfg["data"]["label_col"]
    X_text = df[txtc].astype(str)
    y = df[yc].astype(int).values

    # 2) Признаки
    vec = make_vectorizer(cfg)
    if isinstance(vec, TfidfVectorizer):
        X = vec.fit_transform(X_text)    # offline fit
    else:
        X = vec.transform(X_text)        # hashing, без fit

    # 3) CV объект
    cv_cfg = cfg["cv"]
    if cv_cfg["kind"] == "StratifiedKFold":
        cv = StratifiedKFold(n_splits=cv_cfg["n_splits"], shuffle=cv_cfg["shuffle"], random_state=cfg["seed"])
    else:
        from sklearn.model_selection import KFold
        cv = KFold(n_splits=cv_cfg["n_splits"], shuffle=cv_cfg["shuffle"], random_state=cfg["seed"])

    # 4) Метрики (имена -> функции)
    metric_fn = {
        "accuracy": accuracy_score,
        "f1": f1_score,
        "roc_auc": roc_auc_score,
        "log_loss": log_loss,
    }

    # 5) Какие модели запускать
    todo = cfg["active_models"]
    if args.only:
        only = set([s.strip() for s in args.only.split(",") if s.strip()])
        todo = [m for m in todo if m in only]

    # 6) логирование в experiments.db (создадим таблицы при необходимости)
    def ensure_meta_db(db_path):
        if not cfg["db_log"]["enable"]: return None
        c = sqlite3.connect(db_path)
        c.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS runs(
          id INTEGER PRIMARY KEY,
          ts TEXT, seed INTEGER, config_json TEXT
        );
        CREATE TABLE IF NOT EXISTS models(
          id INTEGER PRIMARY KEY,
          run_id INTEGER REFERENCES runs(id) ON DELETE CASCADE,
          name TEXT, type TEXT, params_json TEXT, path TEXT, train_time REAL
        );
        CREATE TABLE IF NOT EXISTS metrics(
          model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,
          metric TEXT, value REAL, kind TEXT  -- kind: 'cv_mean','cv_std','holdout'
        );
        """)
        return c
    meta = ensure_meta_db(cfg["db_log"]["db_path"]) if cfg["db_log"]["enable"] else None
    run_id = None
    if meta:
        cur = meta.cursor()
        cur.execute("INSERT INTO runs(ts,seed,config_json) VALUES(?,?,?)", (ts(), cfg["seed"], json.dumps(cfg)))
        run_id = cur.lastrowid; meta.commit()

    # 7) цикл по моделям
    for name in todo:
        mcfg = cfg["models"][name]
        mtype = mcfg["type"]
        print(f"=== {name} ({mtype}) ===")

        out_dir = pathlib.Path(cfg["save"]["dir"]) / cfg["save"]["pattern"].format(ts=ts(), model_name=name)
        out_dir.mkdir(parents=True, exist_ok=True)

        t0 = time.time()

        if mtype == "keras_mlp":
            # Классика: train/val сплит внутри fit, метрики по CV можно снять вручную при желании
            model = build_keras_mlp(input_dim=X.shape[1], p=mcfg["params"])
            hist = model.fit(X.toarray(), y,
                             epochs=mcfg["params"]["epochs"],
                             batch_size=mcfg["params"]["batch_size"],
                             validation_split=0.1,
                             verbose=0)
            train_time = time.time() - t0
            model.save(out_dir / "keras_model")
            # базовые метрики на всём трейне (опционально — держите валидационный holdout отдельно)
            y_hat = (model.predict(X.toarray(), verbose=0)[:,0] > 0.5).astype(int)
            res = {
              "accuracy": metric_fn["accuracy"](y, y_hat),
              "f1": metric_fn["f1"](y, y_hat),
            }
            # логирование
            if meta:
                cur = meta.cursor()
                cur.execute(
                  "INSERT INTO models(run_id,name,type,params_json,path,train_time) VALUES(?,?,?,?,?,?)",
                  (run_id, name, mtype, json.dumps(mcfg["params"]), str(out_dir), train_time)
                )
                mid = cur.lastrowid
                for k,v in res.items():
                    cur.execute("INSERT INTO metrics(model_id,metric,value,kind) VALUES(?,?,?,?)",
                                (mid, k, float(v), "train"))
                meta.commit()

        else:
            # sklearn модель (с возможной сеткой)
            Est = import_by_name(mtype)
            est = Est(**(mcfg.get("params") or {}))

            if "grid" in mcfg and mcfg["grid"]:
                gs = GridSearchCV(est, mcfg["grid"], cv=cv, scoring="roc_auc", n_jobs=-1)
                gs.fit(X, y)
                est = gs.best_estimator_
                cv_scores = {"roc_auc": (gs.best_score_, 0.0)}
            else:
                # быстрый кросс-валидационный прогон
                scorers = {m: m for m in cfg["metrics"] if m != "log_loss"}
                cv_res = cross_validate(est, X, y, cv=cv, scoring=scorers, n_jobs=-1, return_train_score=False)
                cv_scores = {m: (float(np.mean(cv_res[f"test_{m}"])), float(np.std(cv_res[f"test_{m}"]))) for m in scorers}
                est.fit(X, y)

            train_time = time.time() - t0
            dump(est, out_dir / "model.joblib")
            # логирование
            if meta:
                cur = meta.cursor()
                cur.execute(
                  "INSERT INTO models(run_id,name,type,params_json,path,train_time) VALUES(?,?,?,?,?,?)",
                  (run_id, name, mtype, json.dumps(mcfg.get("params") or {}), str(out_dir), train_time)
                )
                mid = cur.lastrowid
                for k,(mmean,mstd) in cv_scores.items():
                    cur.execute("INSERT INTO metrics(model_id,metric,value,kind) VALUES(?,?,?,?)",
                                (mid, k, float(mmean), "cv_mean"))
                    cur.execute("INSERT INTO metrics(model_id,metric,value,kind) VALUES(?,?,?,?)",
                                (mid, k, float(mstd), "cv_std"))
                meta.commit()

    if meta: meta.close()
    print("Done.")


if __name__ == "__main__":
    main()