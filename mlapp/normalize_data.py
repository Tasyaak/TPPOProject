import re
from collections import Counter


CV_RE = re.compile(r"\b(const|volatile|restrict)\b")
TAG_PREFIX_RE = re.compile(r"^\s*(struct|class|enum|union)\s+")
WS_RE = re.compile(r"\s+")

INT_WORDS = {
    "short", "int", "long", "signed", "unsigned",
    "__int8", "__int16", "__int32", "__int64",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "size_t", "ptrdiff_t"
}
FLOAT_WORDS = {"float", "double", "long double"}
BOOL_WORDS = {"bool"}
CHAR_WORDS = {"char", "signed char", "unsigned char", "wchar_t", "char8_t", "char16_t", "char32_t"}
VOID_WORDS = {"void"}


def _clean_type_spelling(s : str) -> str:
    s = s or ""
    s = CV_RE.sub(" ", s)
    s = TAG_PREFIX_RE.sub("", s)
    s = WS_RE.sub(" ", s).strip()
    return s

def categorize_type_spelling(type_spelling : str | None) -> str:
    if not type_spelling:
        return "T_UNKNOWN"

    s = _clean_type_spelling(type_spelling)

    if s.endswith(("&&", "&")):
        return "T_REF"

    if "*" in s:
        return "T_PTR"

    if "[" in s and "]" in s:
        return "T_ARRAY"

    if "(" in s and ")" in s:
        return "T_FUNC"

    if "<" in s and ">" in s:
        return "T_TEMPLATE"

    if "::" in s:
        if s.startswith("std::"):
            return "T_STD"
        return "T_NAMESPACE"

    sl = s.lower()
    if sl in VOID_WORDS:
        return "T_VOID"
    if sl in BOOL_WORDS:
        return "T_BOOL"
    if sl in CHAR_WORDS:
        return "T_CHAR"
    if sl in FLOAT_WORDS:
        return "T_FLOAT"

    parts = sl.split()
    if any(p in FLOAT_WORDS for p in parts):
        return "T_FLOAT"
    if any(p in INT_WORDS for p in parts):
        return "T_INT"
    return "T_USER"


def dedupe_preserve_order(xs : list[str]) -> list[str]:
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def core_info_features(core_info : dict ) -> tuple[list[str], dict[str, float]]:
    tokens = []
    numeric = {"N_CORE__HAS_CORE_INFO": 1.0 if core_info else 0.0}
    if not core_info:
        return tokens, numeric

    kind = core_info.get("kind")
    if kind:
        tokens.append(f"F_CORE__KIND={kind}")

    # Бинарные признаки по is_decl/is_expr/is_stmt
    for flag_name in ("is_decl", "is_expr", "is_stmt"):
        flag = core_info.get(flag_name)
        numeric[f"N_CORE__{flag_name.upper()}"] = 1.0 if flag else 0.0

    # Категория типа курсора
    t = core_info.get("type")
    tokens.append(f"F_CORE__TYPE_CAT={categorize_type_spelling(t)}")

    rt = core_info.get("result_type")
    if rt:
        tokens.append(f"F_CORE__RESULT_TYPE_CAT={categorize_type_spelling(rt)}")
    numeric["N_CORE__HAS_RESULT_TYPE"] = 1.0 if rt else 0.0
    return tokens, numeric


def cursor_meta_features(cursor_meta : dict) -> tuple[list[str], dict[str, float]]:
    tokens = []
    numeric = {"N_META__HAS_CURSOR_META": 1.0 if cursor_meta else 0.0}

    if not cursor_meta:
        return tokens, numeric

    # BINARY_OPERATOR
    op = cursor_meta.get("op_spelling")
    if op:
        tokens.append(f"F_META__BINOP_OP={op}")

    lhs_type = cursor_meta.get("lhs_type")
    rhs_type = cursor_meta.get("rhs_type")
    if lhs_type:
        tokens.append(f"F_META__BINOP_LHS_CAT={categorize_type_spelling(lhs_type)}")
    if rhs_type:
        tokens.append(f"F_META__BINOP_RHS_CAT={categorize_type_spelling(rhs_type)}")
    numeric["N_META__HAS_BINOP_OP"] = 1.0 if op else 0.0

    # CALL_EXPR
    num_args = cursor_meta.get("num_args")
    if isinstance(num_args, int):
        numeric["N_META__CALL_N_ARGS"] = float(num_args)

    arg_types = cursor_meta.get("arg_types") or []
    for i, t in enumerate(arg_types[:4]):
        tokens.append(f"F_META__CALL_ARG{i}_CAT={categorize_type_spelling(t)}")
    if len(arg_types) > 4:
        tokens.append("F_META__CALL_ARGS_GT4")

    # DECL_REF_EXPR / MEMBER_REF_EXPR / TYPE_REF
    ref_kind = cursor_meta.get("ref_kind")
    if ref_kind:
        tokens.append(f"F_META__REF_KIND={ref_kind}")

    ref_type = cursor_meta.get("ref_type")
    if ref_type:
        tokens.append(f"F_META__REF_TYPE_CAT={categorize_type_spelling(ref_type)}")
    
    is_type_ref = cursor_meta.get("is_type_ref")
    numeric["N_META__IS_TYPE_REF"] = 1.0 if is_type_ref else 0.0
    return tokens, numeric


IO_HEADERS = {"iostream", "iomanip", "cstdio", "stdio", "fstream", "sstream", "istream", "ostream", "ifstream", "ofstream"}
CONTAINER_HEADERS = {
    "vector", "list", "forward_list", "deque", "map", "multimap", "unordered_map", "unordered_multimap", "set",
    "multiset", "unordered_set", "queue", "priority_queue", "stack", "array", "valarray", "bitset"
}
ALG_HEADERS = {"algorithm", "numeric", "functional"}
MATH_HEADERS = {"math", "cmath", "complex", "random"}
STRING_HEADERS = {"string", "string_view", "cstring", "cwchar", "sstream", "streambuf", "regex"}
THREAD_HEADERS = {"thread", "mutex", "condition_variable", "future"}

def include_category(h : str) -> str | None:
    base = (h or "").split("/")[-1].split("\\")[-1]
    base = base.split(".")[0]
    if base in IO_HEADERS: return "IO"
    if base in CONTAINER_HEADERS: return "CONTAINER"
    if base in ALG_HEADERS: return "ALGO"
    if base in MATH_HEADERS: return "MATH"
    if base in STRING_HEADERS: return "STRING"
    if base in THREAD_HEADERS: return "THREAD"
    return None


def build_features_from_ctx(ctx : dict) -> tuple[list[str], dict[str, float]]:
    tokens = []
    numeric = {}

    if not ctx:
        return tokens, numeric

    # Локальные токены вокруг ошибки
    local = ctx.get("local_tokens_norm") or []
    tokens.extend([f"F_TOK={t}" for t in local])
    numeric["N_TOK__LOCAL_TOK_LEN"] = float(len(local))

    # core_info / cursor_meta
    core_info = ctx.get("core_info") or {}
    cursor_meta = ctx.get("cursor_meta") or {}
    tokens_core, numeric_core = core_info_features(core_info)
    tokens_meta, numeric_meta = cursor_meta_features(cursor_meta)
    tokens.extend(tokens_core)
    tokens.extend(tokens_meta)
    numeric.update(numeric_core)
    numeric.update(numeric_meta)

    # parent_chain
    parent_chain = ctx.get("parent_chain") or []
    for depth, kind in enumerate(parent_chain):
        tokens.append(f"F_PARENT__D{depth}={kind}")
    for kind in dedupe_preserve_order(parent_chain):
        tokens.append(f"F_PARENT__KIND={kind}")
    numeric["N_PARENT__CHAIN_LEN"] = float(len(parent_chain))

    # includes
    includes = ctx.get("includes") or []
    numeric["N_INC__INCLUDES"] = float(len(includes))

    inc_cats = []
    for h in includes:
        cat = include_category(h)
        if cat:
            inc_cats.append(cat)
    for cat in dedupe_preserve_order(inc_cats):
        tokens.append(f"F_INC__CAT={cat}")

    # Макросы и препроцессор
    macros = ctx.get("macros") or []
    if macros:
        n_macro_def = sum(1 for m in macros if (m.get("kind") == "macro_def"))
        n_macro_use = sum(1 for m in macros if (m.get("kind") == "macro_use"))
        n_pp_dir = sum(1 for m in macros if (m.get("kind") == "pp_directive"))
        numeric["N_MACRO__DEF"] = float(n_macro_def)
        numeric["N_MACRO__USE"] = float(n_macro_use)
        numeric["N_MACRO__PP_DIRECTIVE"] = float(n_pp_dir)
    numeric["N_MACRO__HAS_MACROS"] = 1.0 if macros else 0.0
        

    # using / typedef / namespaces  
    aliases_ns = ctx.get("aliases_ns") or {}
    using_directives = aliases_ns.get("using_directives") or []
    using_decls = aliases_ns.get("using_decls") or []
    typedefs = aliases_ns.get("typedefs") or []
    namespaces = aliases_ns.get("namespaces") or []

    numeric["N_USING__DIRECTIVES"] = float(len(using_directives))
    numeric["N_USING__DECLS"] = float(len(using_decls))
    numeric["N_TYPEDEF__TYPEDEFS"] = float(len(typedefs))
    numeric["N_NS__NAMESPACES"] = float(len(namespaces))

    # токены по using namespace X;
    for ns in dedupe_preserve_order(using_directives):
        tokens.append(f"F_USING_NS__NS={ns}")

    # typedefs
    td_cats = Counter()
    for td in typedefs:
        under = td.get("underlying")
        td_cats[categorize_type_spelling(under)] += 1

    for cat, cnt in td_cats.items():
        tokens.append(f"F_TYPEDEF__UNDER_CAT={cat}")
        numeric[f"N_TYPEDEF__UNDER__{cat}"] = float(cnt)

    # Декларации типов/переменных/функций
    decls = ctx.get("decls") or {}
    type_kind_counts = decls.get("type_kind_counts") or {}
    var_kind_counts = decls.get("var_kind_counts") or {}
    func_kind_counts = decls.get("func_kind_counts") or {}
    var_type_counts = decls.get("var_type_counts") or {}

    for k, v in type_kind_counts.items():
        numeric[f"N_DECL__TYPE_KIND__{k}"] = float(v)
    for k, v in var_kind_counts.items():
        numeric[f"N_DECL__VAR_KIND__{k}"] = float(v)
    for k, v in func_kind_counts.items():
        numeric[f"N_DECL__FUNC_KIND__{k}"] = float(v)

    numeric["N_DECL__TYPES_TOTAL"] = float(sum(type_kind_counts.values())) if type_kind_counts else 0.0
    numeric["N_DECL__VARS_TOTAL"] = float(sum(var_kind_counts.values())) if var_kind_counts else 0.0
    numeric["N_DECL__FUNCS_TOTAL"] = float(sum(func_kind_counts.values())) if func_kind_counts else 0.0

    vt_cat = Counter()
    for t_sp, cnt in var_type_counts.items():
        vt_cat[categorize_type_spelling(t_sp)] += cnt

    for cat, cnt in vt_cat.items():
        tokens.append(f"F_DECL__VARS_TYPE_CAT={cat}")
        numeric[f"N_DECL__VARS_TYPE__{cat}"] = float(cnt)

    if "STRUCT_DECL" in type_kind_counts:
        numeric["N_DECL__HAS_STRUCT"] = 1.0
    if "CLASS_DECL" in type_kind_counts:
        numeric["N_DECL__HAS_CLASS"] = 1.0
    if "ENUM_DECL" in type_kind_counts:
        numeric["N_DECL__HAS_ENUM"] = 1.0
    if "CLASS_TEMPLATE" in type_kind_counts:
        numeric["N_DECL__HAS_CLASS_TEMPLATE"] = 1.0
    return tokens, numeric


def normalize_error_text(error_text : str) -> str:
    res = ""
    error_code = error_text[:5]
    match error_code:
        case 'C2065':
            res = re.sub(r': ([^:]+):', ': <IDENT>:', error_text, count=1)
        case 'C3861' | 'C2672':
            res = re.sub(r': ([^:]+):', ': <FUNC>:', error_text, count=1)
        case 'C2039':
            temp = re.sub(r'"[^"]+"', '<IDENT>', error_text, count=1)
            res = re.sub(r'"[^"]+"', '<DECL>', temp, count=1)
        case 'C2143':
            error_text = re.sub('"user-defined string literal"|"user-defined literal"|"константа"|"строка"|user-defined string literal|user-defined literal|константа|строка', '<LITER>', error_text)
            temp = re.sub(r'"[^"]+"', '<TOKEN>', error_text, count=1)
            res = re.sub(r'"[^"]+"', '<IDENT>', temp, count=1)
        case 'C2146':
            temp = re.sub(r'"[^"]+"', '<TOKEN>', error_text, count=1)
            res = re.sub(r'"[^"]+"', '<IDENT>', temp, count=1)
        case 'C2059':
            error_text = re.sub('"user-defined string literal"|"user-defined literal"|"константа"|"строка"|user-defined string literal|user-defined literal|константа|строка', '<LITER>', error_text)
            res = re.sub(r'(?<=: )(?:(?!<LITER>$)\w+)$', '<IDENT>', error_text)
        case 'C2144':
            temp = re.sub(r'"[^"]+"', '<TYPE>', error_text, count=1)
            res = re.sub(r'"[^"]+"', '<TOKEN>', temp, count=1)
        case 'C2187':
            res = re.sub(r'"[^"]+"', '<IDENT>', error_text, count=1)
        case 'C1075':
            res = re.sub(r'"\{"', '<BRACE>', error_text, count=1)
        case 'C2131' | 'C2148' | 'C2181':
            res = error_text
        case 'C2440':
            temp1 = re.sub(r': ([^:]+):', ': <CONTEXT>', error_text, count=1)
            temp2 = re.sub(r'"[^"]+"', '<TYPE_1>', temp1, count=1)
            res = re.sub(r'"[^"]+"', '<TYPE_2>', temp2, count=1)
        case 'C2446':
            temp1 = re.sub(r'^(.*?:\s*)(\S+?)(?=\s|:)', r'\1<OPER>', error_text, count=1)
            temp2 = re.sub(r'"[^"]+"', '<TYPE_1>', temp1, count=1)
            res = re.sub(r'"[^"]+"', '<TYPE_2>', temp2, count=1)
        case 'C2676' | 'C2678' | 'C2679':
            temp = re.sub(r'"[^"]+"', '<OPER>', error_text, count=1)
            res = re.sub(r'"[^"]+"', '<TYPE>', temp, count=1)
        case 'C2064':
            res = re.sub(r'принимающая \d+', 'принимающая <NUM>', error_text, count=1)
        case 'C1083':
            res = re.sub(r'^((?:[^:]*:){2}).*$', r'\1 <PATH>', error_text)
        case 'C2106':
            res = re.sub(r': \S+:', ': <OPER>:', error_text, count=1)
    return res


TOKEN_RE = re.compile(
    r"<[A-Z0-9_]+>|C\d{4}|[A-Za-zА-Яа-яЁё0-9_]+",
    re.VERBOSE
)

def error_tokenizer(text : str) -> list[str]:
    return TOKEN_RE.findall(text)


def test_normalize_error_code() -> None:
    error_text = input()
    temp = normalize_error_text(error_text)
    res = error_tokenizer(temp)
    print(temp, res, sep="\n")


if __name__ == "__main__":
    test_normalize_error_code()