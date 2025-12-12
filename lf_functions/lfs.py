import re, difflib
from pandas import Series
from .details import *


def lf_C2065_HEADER_OR_STD_NAMESPACE(row : Series) -> str | None:
    if row.get("error_code") != "C2065":
        return None

    ident = extract_ident(row.get("error_text", ""))
    if not ident:
        return None

    ident_clean = ident.strip()

    if ident_clean in KNOWN_STD_IDENTIFIERS_FOR_HEADER:
        return "HEADER_OR_STD_NAMESPACE"
    
    stripped = ident_clean.lstrip("?$")
    if stripped in KNOWN_STD_IDENTIFIERS_FOR_HEADER:
        return "HEADER_OR_STD_NAMESPACE"
    return None


def lf_C2065_FIX_NAME_SPELLING(row : Series) -> str | None:
    if row.get("error_code") != "C2065":
        return None

    error_text = row.get("error_text", "")
    source_code = row.get("source_code", "")
    error_line = row["error_line"]

    ident = extract_ident(error_text)
    if not ident:
        return None

    ident_clean = ident.strip()

    if re.search(r"[^A-Za-z0-9_]", ident_clean):
        return "FIX_NAME_SPELLING"

    if ident_clean in KNOWN_STD_IDENTIFIERS_FOR_HEADER:
        return None

    src = source_code.replace('\\n', '\n')
    line = extract_line_concat(src, error_line)

    if is_type_like_context(line, ident_clean):
        best_kw, best_score = None, 0.0
        for kw in TYPE_KEYWORDS:
            score = difflib.SequenceMatcher(None, ident_clean, kw).ratio()
            if score > best_score:
                best_kw, best_score = kw, score
        if best_kw and is_keyword_typo(ident_clean, best_kw, best_score):
            return "FIX_NAME_SPELLING"
        return None
    
    best_ctrl, best_ctrl_score = None, 0.0
    for kw in CONTROL_KEYWORDS:
        score = difflib.SequenceMatcher(None, ident_clean, kw).ratio()
        if score > best_ctrl_score:
            best_ctrl, best_ctrl_score = kw, score
    if best_ctrl and is_keyword_typo(ident_clean, best_ctrl, best_ctrl_score):
        if is_control_like_context(line, ident_clean):
            return "FIX_NAME_SPELLING"
        return None

    candidates = extract_identifier_candidates(source_code, error_line=error_line, window=10)
    candidates.discard(ident_clean)

    best = find_best_match(ident_clean, candidates, cutoff=0.8)
    if best is not None:
        return "FIX_NAME_SPELLING"
    return None


def lf_C3861_HEADER_OR_STD_NAMESPACE(row : Series) -> str | None:
    if row.get("error_code") != "C3861":
        return None

    ident = extract_ident(row.get("error_text", ""))
    if not ident:
        return None

    ident_clean = ident.strip()

    if ident_clean in KNOWN_STD_IDENTIFIERS_FOR_HEADER:
        return "HEADER_OR_STD_NAMESPACE"

    stripped = ident_clean.lstrip("?$")
    if stripped in KNOWN_STD_IDENTIFIERS_FOR_HEADER:
        return "HEADER_OR_STD_NAMESPACE"
    return None


def lf_C3861_FIX_NAME_SPELLING(row : Series) -> str | None:
    if row.get('error_code') != 'C3861':
        return None

    error_text = row.get('error_text', '')
    source_code = row.get('source_code', '')
    error_line = row['error_line']

    ident = extract_ident(error_text)
    if not ident:
        return None

    ident_clean = ident.strip()

    if re.search(r"[^A-Za-z0-9_]", ident_clean):
        return 'FIX_NAME_SPELLING'

    if ident_clean in CPP_FUNCTIONS:
        return None
    
    src = source_code.replace("\\n", "\n")
    line = extract_line_concat(src, error_line)

    best_loop_kw, best_loop_score = None, 0.0
    for kw in LOOP_KEYWORDS:
        score = difflib.SequenceMatcher(None, ident_clean, kw).ratio()
        if score > best_loop_score:
            best_loop_kw, best_loop_score = kw, score
    if best_loop_kw and is_keyword_typo(ident_clean, best_loop_kw, best_loop_score):
        if is_loop_like_context(line, ident_clean):
            return 'FIX_NAME_SPELLING'
        return None
        
    best_name, best_score = None, 0.0
    for std_name in CPP_FUNCTIONS:
        score = difflib.SequenceMatcher(None, ident_clean, std_name).ratio()
        if score > best_score:
            best_name, best_score = std_name, score
    if best_name and is_keyword_typo(ident_clean, best_name, best_score):
        return 'FIX_NAME_SPELLING'
    
    candidates = extract_function_candidates(source_code, error_line=error_line, window=10)
    candidates.discard(ident_clean)

    best = find_best_match(ident_clean, candidates, cutoff=0.8)
    if best is not None:
        return 'FIX_NAME_SPELLING'
    return None


def lf_C2146_INCORRECT_CONSTRUCTION_OR_SYMBOLS(row : Series) -> str | None:
    if row.get("error_code") != "C2146":
        return None

    error_text = row.get("error_text", "")
    source_code = row.get("source_code", "")
    error_line = row["error_line"]

    ident_err = extract_ident_c2146(error_text)
    if not ident_err:
        return None
    if not isinstance(source_code, str):
        return None

    src = source_code.replace('\\n', '\n')
    line = pick_focus_line(extract_lines(src, error_line), ident_err)
    # 1) cin/cout и т.п.
    if stream_missing_shift(line):
        # print(error_text, line, sep="\n")
        # print("cin/cout")
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    # 2) for-шапка: нехватка ';' (но не range-for)
    if for_header_missing_semicolon(line):
        # print(error_text, line, sep="\n")
        # print("for")
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    # 3) пропуск разделителя в аргументах вызова
    if missing_sep_in_call_args(line, ident_err):
        # print(error_text, line, sep="\n")
        # print("func")
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    # 4) пропуск оператора/разделителя в условии if/while/switch
    if missing_op_in_condition(line, ident_err):
        # print(error_text, line, sep="\n")
        # print("if/while/switch")
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    # 5) общий случай: рядом с ident_err есть "идентификатор идентификатор" перед = , ; ) ] {
    if adjacent_idents_need_separator_decl_only(line, ident_err):
        # print(error_text, line, sep="\n")
        # print("type")
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    return None