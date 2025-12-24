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
    src = normalize_src_text(row.get("source_code", ""))
    error_line = row["error_line"]

    ident = extract_ident(error_text)
    if not ident:
        return None

    ident_clean = ident.strip()

    if re.search(r"[^A-Za-z0-9_]", ident_clean):
        return "FIX_NAME_SPELLING"

    if ident_clean in KNOWN_STD_IDENTIFIERS_FOR_HEADER:
        return None

    window = extract_lines_window(src, error_line, radius=1)
    line = "\n".join(window)

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

    candidates = extract_identifier_candidates(src, error_line=error_line, window=10)
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
    src = normalize_src_text(row.get('source_code', ''))
    error_line = row['error_line']

    ident = extract_ident(error_text)
    if not ident:
        return None

    ident_clean = ident.strip()

    if re.search(r"[^A-Za-z0-9_]", ident_clean):
        return 'FIX_NAME_SPELLING'

    if ident_clean in CPP_FUNCTIONS:
        return None
    
    window = extract_lines_window(src, error_line, radius=1)
    line = "\n".join(window)

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
    
    candidates = extract_function_candidates(src, error_line=error_line, window=10)
    candidates.discard(ident_clean)

    best = find_best_match(ident_clean, candidates, cutoff=0.8)
    if best is not None:
        return 'FIX_NAME_SPELLING'
    return None


def lf_C2146_INCORRECT_CONSTRUCTION_OR_SYMBOLS(row : Series) -> str | None:
    if row.get("error_code") != "C2146":
        return None

    error_text = row.get("error_text", "")
    src = normalize_src_text(row.get("source_code", ""))
    error_line = row["error_line"]

    ident_err = extract_ident_c2146(error_text)
    if not ident_err:
        return None
    if not isinstance(src, str):
        return None

    line = pick_focus_line(extract_lines_window(src, error_line, radius=1), ident_err)
    # 1) cin/cout и т.п.
    if stream_missing_shift(line):
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    # 2) for-шапка: нехватка ';' (но не range-for)
    if for_header_missing_semicolon(line):
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    # 3) пропуск разделителя в аргументах вызова
    if missing_sep_in_call_args(line, ident_err):
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    # 4) пропуск оператора/разделителя в условии if/while/switch
    if missing_op_in_condition(line, ident_err):
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    # 5) общий случай: рядом с ident_err есть "идентификатор идентификатор" перед = , ; ) ] {
    if adjacent_idents_need_separator_decl_only(line, ident_err):
        return "INCORRECT_CONSTRUCTION_OR_SYMBOLS"
    return None


def lf_C2440_FIX_CAST(row : Series) -> str | None:
    if row.get("error_code") != "C2440":
        return None

    error_text = row.get("error_text", "")
    src = normalize_src_text(row.get("source_code", ""))
    err_line = row["error_line"]

    if not isinstance(error_text, str) or not isinstance(src, str):
        return None

    _, to_t = extract_c2440_types(error_text)
    if not to_t:
        return None

    to_type_pat = build_to_type_pattern(to_t)
    window = extract_lines_window(src, err_line, radius=1)

    for line in window:
        if has_explicit_cast(line, to_type_pat):
            return "FIX_CAST"
    return None


def lf_C2446_FIX_POINTERS_FOR_CAST(row : Series) -> str | None:
    if row.get("error_code") != "C2446":
        return None

    error_text = row.get("error_text", "")
    src = normalize_src_text(row.get("source_code", ""))
    error_line = row["error_line"]

    if not isinstance(error_text, str) or not isinstance(src, str):
        return None
    # print(error_text)

    op = extract_c2446_op(error_text)
    if op not in CMP_OPS:
        return None
    # print(f"op = {op}")

    window = extract_lines_window(src, error_line, radius=1)
    focus_lines = [ln for ln in window if op in ln]
    if not focus_lines:
        # print("no oper in src")
        return None
    
    window_text = "\n".join(focus_lines)
    # print(window_text)

    if CONTENT_CMP_FUN_RE.search(window_text):
        # print("strcmp/memcmp")
        return None
    if has_nullptr_comparison(window_text, op):
        # print("pointer with 0/nullptr comp")
        return None
    
    # Извлечём типы из error_text (насколько возможно)
    quoted = extract_quoted_tokens(error_text)
    type_tokens = [t for t in quoted if looks_like_type(t)]

    ptr_like_types = [t for t in type_tokens if PTR_OR_ARR_RE.search(t)]
    if not ptr_like_types:
        # print("ptr_like_types is None")
        return None
    
    has_char_arr = any(is_char_array_type(t) for t in type_tokens)
    has_arith = any(is_arith_type(t) for t in type_tokens)
    if has_string_literal_in_comparison(window_text, op):
        if FIND_PRECEDENCE_RE.search(window_text):
            # print("str_liter comp")
            return None
        if has_char_arr and has_arith:
            # print("str_liter comp")
            return None
        
    if op in { "==", "!=" }:
        if len(ptr_like_types) >= 2 and any(CHARLIKE_RE.search(t) for t in ptr_like_types):
            if has_string_literal(window_text):
                # print("char-like comp str_liter error")
                return "FIX_POINTERS_FOR_CAST"
        if len(ptr_like_types) == 1 and len(type_tokens) >= 2:
            other_types = [t for t in type_tokens if t not in ptr_like_types]
            if other_types and not has_nullptr_comparison(window_text, op):
                    # print("pointer comp error")
                    return "FIX_POINTERS_FOR_CAST"
    if len(ptr_like_types) >= 2 and any(CHARLIKE_RE.search(t) for t in ptr_like_types):
        # print("char-like comp error")
        return "FIX_POINTERS_FOR_CAST"
    return None


def lf_C2676_FIX_EXPR_FOR_OPERATOR(row : Series) -> str | None:
    if row.get("error_code") != "C2676":
        return None

    error_text = row.get("error_text", "")
    src = normalize_src_text(row.get("source_code", ""))
    error_line = row["error_line"]

    if not isinstance(error_text, str) or not isinstance(src, str):
        return None

    # print(f"error_text = {error_text}")
    op, quoted = extract_c2676_op_and_types(error_text)

    if (not op) and quoted and quoted[0] in OPS_SET:
        op = quoted[0]

    if not op:
        # print("op in None")
        return None
    # print(f"op = {op}")

    first_type = choose_best_type_candidate(quoted, op)
    outer = outer_type(first_type)
    # print(f"outer = {outer}")

    is_ostream = bool(OSTREAM_TYPE_RE.search(error_text) or OSTREAM_TYPE_RE.search(first_type))
    is_istream = bool(ISTREAM_TYPE_RE.search(error_text) or ISTREAM_TYPE_RE.search(first_type))

    if is_ostream and op in {"<", ">", ">>", ">>=", "<<="}:
        # print("cout wrong direction (>>)")
        return None

    if is_istream and op in {"<", ">", "<<", ">>=", "<<="}:
        # print("cin wrong direction (<<)")
        return None
    
    window = extract_lines_window(src, error_line, radius=2)
    window_text = "\n".join(window)
    # print(window_text)

    is_iterator = bool(ITERATOR_TYPE_RE.search(outer) or ITERATOR_TYPE_RE.search(first_type) or ITERATOR_TYPE_RE.search(error_text))

    if is_iterator and op in (ITER_COMPLEX_WRONG_CMP_OPS | ITER_WRONG_ARITH_OPS):
        # print("iterator oper error")
        return "FIX_EXPR_FOR_OPERATOR"
    
    is_complex = bool(COMPLEX_TYPE_RE.search(outer) or COMPLEX_TYPE_RE.search(first_type) or COMPLEX_TYPE_RE.search(error_text))
    if is_complex and op in (ARITH_OPS | {"++", "--"}):
        # print("complex oper error")
        return "FIX_EXPR_FOR_OPERATOR"
    
    is_string_outer = bool(outer in {"std::string", "std::basic_string"} or STRING_TYPE_RE.search(outer))
    if is_string_outer and op in {"<<", ">>", "==", "!=", "<", ">", "<=", ">=", "+=", "-=", ">>=", "<<="}:
        # print("string oper error")
        return "FIX_EXPR_FOR_OPERATOR"
    
    is_pair_outer = bool(PAIR_TYPE_RE.search(outer))
    if is_pair_outer and op in CMP_OPS:
        # print("pair comp error")
        return "FIX_EXPR_FOR_OPERATOR"
        
    if op == "[":
        if NON_INDEXABLE_STL_RE.search(outer) or NON_INDEXABLE_STL_RE.search(first_type) or NON_INDEXABLE_STL_RE.search(error_text):
            # print("non-indexable STL [] error")
            return "FIX_EXPR_FOR_OPERATOR"
        if (STL_CONTAINER_RE.search(outer) or STL_CONTAINER_RE.search(first_type) or STL_CONTAINER_RE.search(error_text)) and \
                not (INDEXABLE_STL_RE.search(outer) or INDEXABLE_STL_RE.search(first_type) or INDEXABLE_STL_RE.search(error_text)):
            # print("STL container without operator[] error")
            return "FIX_EXPR_FOR_OPERATOR"

    if op in ARITH_OPS:
        if STL_CONTAINER_RE.search(outer) or STL_CONTAINER_RE.search(first_type) or STL_CONTAINER_RE.search(error_text):
            # print("STL arithmetic error")
            return "FIX_EXPR_FOR_OPERATOR"
        
    if outer and (not STL_CONTAINER_RE.search(outer)) and (not is_ostream) and (not is_istream):
        if op in (ARITH_OPS | CMP_OPS | {"++", "--", "&", "|", "^", "&&", "||"}):
            # print("user-defined type operator mismatch error")
            return "FIX_EXPR_FOR_OPERATOR"

    # print("nothing")
    return None


def lf_C2678_FIX_LEFT_OPERAND(row : Series) -> str | None:
    if row.get("error_code") != "C2678":
        return None

    error_text = row.get("error_text", "")
    src = normalize_src_text(row.get("source_code", ""))
    error_line = row["error_line"]
    # print(error_text)

    op, lhs_raw = extract_c2678_op_lhs(error_text)
    if not op or not lhs_raw:
        return None
    lhs_outer, lhs_quals = split_outer_and_qualifiers(lhs_raw)
    # print(f"lhs_outer = {lhs_outer}, lhs_quals = {lhs_quals}")

    is_ostream = bool(OSTREAM_TYPE_RE.search(lhs_outer))
    is_istream = bool(ISTREAM_TYPE_RE.search(lhs_outer))

    if is_ostream and op in {"<", ">", ">>"}:
        # print("cout no error")
        return None
    if is_istream and op in {"<", ">", "<<"}:
        # print("cin no error")
        return None
    
    is_const_lhs = ("const" in lhs_quals)
    if is_const_lhs and op in MUTATING_OPS:
        # print("const error")
        return "FIX_LEFT_OPERAND"
    
    is_complex = bool(COMPLEX_TYPE_RE.search(lhs_outer) or COMPLEX_TYPE_RE.search(lhs_raw) or COMPLEX_TYPE_RE.search(error_text))
    if is_complex and op in ITER_COMPLEX_WRONG_CMP_OPS:
        # print("complex oper error")
        return "FIX_LEFT_OPERAND"
    
    window = extract_lines_window(src, error_line, radius=2)

    focus_lines = [ln for ln in window if op in ln]
    window_text = "\n".join(focus_lines if focus_lines else window)
    # print(window_text)

    is_string_lhs = bool(STRING_TYPE_RE.search(lhs_outer) or STRING_TYPE_RE.search(lhs_raw) or STRING_TYPE_RE.search(error_text))
    if is_string_lhs and op in {"&&", "||"}:
        t = strip_cpp_literals(window_text)
        t = SHIFT_OP_RE.sub(" ", t)
        if not BOOLISH_STRING_CTX_RE.search(t):
            # print("string bool error")
            return "FIX_LEFT_OPERAND"
    
    if is_ostream:
        if op in STREAM_PRECEDENCE_OPS and has_shift_before_op(window_text, COUT_SHIFT_RE, op, any_shift_pat=ANY_INSERT_RE):
            # print("cout error")
            return "FIX_LEFT_OPERAND"
        
    if is_istream:
        if op in {"==", "!="}:
            t_stripped = strip_cpp_literals(window_text)
            eof_like = bool(EOF_RE.search(t_stripped)) or bool(EOF_STR_LIT_RE.search(window_text))
            rhs = t_stripped.split(op, 1)[1] if op in t_stripped else ""
            const_like = bool(ISTREAM_CONST_RHS_RE.search(rhs))
            if (eof_like or const_like) and has_shift_before_op(window_text, CIN_SHIFT_RE, op, any_shift_pat=ANY_EXTRACT_RE):
                # print("cin error")
                return "FIX_LEFT_OPERAND"
            
        if op in {"&&", "||"} and has_shift_before_op(window_text, CIN_SHIFT_RE, op, any_shift_pat=ANY_EXTRACT_RE):
            # print("cin error")
            return "FIX_LEFT_OPERAND"
        if op in {"&", "|"} and has_shift_before_op(window_text, CIN_SHIFT_RE, op, any_shift_pat=ANY_EXTRACT_RE):
            rhs = window_text.split(op, 1)[1] if op in window_text else ""
            if BOOL_RHS_HINT_RE.search(rhs):
                # print("cin error")
                return "FIX_LEFT_OPERAND"

    # print("nothing")
    return None


def lf_C2679_FIX_RIGHT_OPERAND(row : Series) -> str | None:
    if row.get("error_code") != "C2679":
        return None

    error_text = row.get("error_text", "")
    src = normalize_src_text(row.get("source_code", ""))
    error_line = row["error_line"]

    if not isinstance(error_text, str) or not isinstance(src, str):
        return None
    # print(error_text)

    op, rhs_raw = extract_c2679_op_rhs(error_text)
    if not op or not rhs_raw:
        return None
    # print(f"rhs_raw = {rhs_raw}")

    window = extract_lines_window(src, error_line, radius=2)
    focus = focus_lines_by_op(window, op)
    window_text = "\n".join(focus if focus else window)
    # print(window_text)

    if VOID_TYPE_RE.search(rhs_raw):
        # print("void error")
        return "FIX_RIGHT_OPERAND"

    if op in {"<<", ">>"} and OVERLOADED_FN_RE.search(rhs_raw):
        # print("overload error")
        return "FIX_RIGHT_OPERAND"

    if op == ">>":
        if CONST_CHAR_ARR_RE.search(rhs_raw):
            # print("cin str liter error")
            return "FIX_RIGHT_OPERAND"
        
        if CONST_RE.search(rhs_raw):
            # print("cin const error")
            return "FIX_RIGHT_OPERAND"
        
        if ARRAY_TYPE_RE.search(rhs_raw) and not CHARLIKE_RE.search(rhs_raw):
            # print("cin mass error")
            return "FIX_RIGHT_OPERAND"
        
        if "*" in rhs_raw and not CHARLIKE_RE.search(rhs_raw):
            # print("cin pointer error")
            return "FIX_RIGHT_OPERAND"
        
        if STL_CONTAINER_RE.search(rhs_raw) or STL_CONTAINER_RE.search(error_text):
            # print("cin STL error")
            return "FIX_RIGHT_OPERAND"

    if op == "<<":
        if ITERATOR_TYPE_RE.search(rhs_raw):
            # print("cout iter error")
            return "FIX_RIGHT_OPERAND"
        if PAIR_TYPE_RE.search(rhs_raw):
            # print("cout pair error")
            return "FIX_RIGHT_OPERAND"
        if STL_CONTAINER_RE.search(rhs_raw) or STL_CONTAINER_RE.search(error_text):
            # print("cout STL error")
            return "FIX_RIGHT_OPERAND"

    if op == "[":
        if MULTICHAR_IN_BRACKETS_RE.search(window_text):
            # print("multisymbol error")
            return "FIX_RIGHT_OPERAND"
        
    if op == "=":
        if STL_CONTAINER_RE.search(rhs_raw):
            # print("STL = error")
            return "FIX_RIGHT_OPERAND"

    if op in ARITH_OPS:
        if PTR_OR_ARR_TYPE_RE.search(rhs_raw) and not CHARLIKE_RE.search(rhs_raw):
            # print("ponter arith error")
            return "FIX_RIGHT_OPERAND"
        if ITERATOR_TYPE_RE.search(rhs_raw) or PAIR_TYPE_RE.search(rhs_raw):
            # print("iter/pair arith error")
            return "FIX_RIGHT_OPERAND"
        
    # print("nothing")
    return None