import joblib, json
from config import MODELS_DIR

# def

pipe = joblib.load(MODELS_DIR / "model.joblib")
meta = json.loads((MODELS_DIR / "meta.json").read_text(encoding="utf-8"))


# пример инференса
# import pandas as pd
# df_new = pd.DataFrame([{
#     "ctx_tokens": '["int","main","(",")"]',
#     "error_text_tokens": '["C2679",":","..."]',
#     "ctx_numeric": '{"has_template": 1, "n_ptr": 0}'
# }])

# pred = pipe.predict(df_new)
# proba = pipe.predict_proba(df_new)
