import json, numpy as np


def _tokens_col_to_tokens(X):
    col = np.asarray(X).reshape(-1)
    return [json.loads(s) for s in col]


def _dict_col_to_dicts(X):
    col = np.asarray(X).reshape(-1)
    return [json.loads(s) for s in col]


def _identity(x):
    return x