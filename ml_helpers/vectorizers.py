from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler, MaxAbsScaler
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import CountVectorizer, HashingVectorizer, TfidfVectorizer
from sklearn.compose import ColumnTransformer
from .transformers import _identity, _dict_col_to_dicts, _tokens_col_to_tokens


PREPROCESSORS = {
    "identity": _identity,
}
TOKENIZERS = {
    "identity": _identity,
}

def build_text_tokens(field_cfg : dict, *, lowercase : bool, naive_bayes_compatible : bool) -> Pipeline:
    mode = field_cfg["mode"]
    ngram_range = tuple(field_cfg["ngram_range"])
    token_pattern = field_cfg["token_pattern"]

    tokenizer_name = field_cfg["tokenizer"]
    preprocessor_name = field_cfg["preprocessor"]

    preprocessor = PREPROCESSORS[preprocessor_name]
    tokenizer = TOKENIZERS[tokenizer_name]
    
    if mode == "CountVectorizer":
        base_params = dict(field_cfg["CountVectorizer"])
        vect = CountVectorizer(
            lowercase=lowercase,
            ngram_range=ngram_range,
            preprocessor=preprocessor,
            tokenizer=tokenizer,
            token_pattern=token_pattern,
            **base_params,
        )
    elif mode == "HashingVectorizer":
        base_params = dict(field_cfg["HashingVectorizer"])
        if naive_bayes_compatible:
            base_params["alternate_sign"] = False  # чтобы не получить отрицательные значения
        vect = HashingVectorizer(
            lowercase=lowercase,
            ngram_range=ngram_range,
            preprocessor=preprocessor,
            tokenizer=tokenizer,
            token_pattern=token_pattern,
            **base_params,
        )
    elif mode == "TfidfVectorizer":
        base_params = dict(field_cfg["TfidfVectorizer"])
        vect = TfidfVectorizer(
            lowercase=lowercase,
            ngram_range=ngram_range,
            preprocessor=preprocessor,
            tokenizer=tokenizer,
            token_pattern=token_pattern,
            **base_params,
        )
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    scaler_name = field_cfg["scaler"]
    if scaler_name == "MaxAbsScaler":
        scaler = MaxAbsScaler()
    else:
        raise ValueError(f"Unsupported scaler: {scaler_name}")
    
    to_tokens = FunctionTransformer(_tokens_col_to_tokens, validate=False)
    steps = [("to_tokens", to_tokens), ("vect", vect), ("scale", scaler)]
    return Pipeline(steps)


def build_numeric_dict(field_cfg : dict) -> Pipeline:
    mode = field_cfg["mode"]
    scale = field_cfg["scale"]

    if mode == "DictVectorizer":
        base_params = dict(field_cfg["vectorizers"]["DictVectorizer"])
        dv = DictVectorizer(**base_params)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    if scale == "StandardScaler":
        base_params = dict(field_cfg["scaling"]["StandardScaler"])
        sc = StandardScaler(**base_params)
    else:
        raise ValueError(f"Unsupported scaling: {scale}")

    ctx_vec = Pipeline([
            ("to_dicts", FunctionTransformer(_dict_col_to_dicts, validate=False)),
            ("dv", dv),
            ("scale", sc),
    ])
    return ctx_vec


def build_vectorizer_from_cfg(cfg : dict, *, col_map : dict[str, str] | None = None) -> ColumnTransformer:
    features = cfg["features"]
    lowercase = bool(features["lowercase"])
    nb_ok = bool(features["naive_bayes_compatible"])

    col_map = col_map or {
        "for_ctx_numeric": "ctx_numeric",
        "for_ctx_tokens": "ctx_tokens",
        "for_error_text": "error_text_tokens",
    }

    tr = []

    tr.append((
        "source_code",
        build_text_tokens(features["for_ctx_tokens"], lowercase=lowercase, naive_bayes_compatible=nb_ok),
        col_map["for_ctx_tokens"],
    ))

    tr.append((
        "error_text",
        build_text_tokens(features["for_error_text"], lowercase=lowercase, naive_bayes_compatible=nb_ok),
        col_map["for_error_text"],
    ))

    tr.append((
        "ctx_numeric",
        build_numeric_dict(features["for_ctx_numeric"]),
        col_map["for_ctx_numeric"],
    ))

    return ColumnTransformer(transformers=tr, remainder="drop")