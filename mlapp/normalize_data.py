import re
from processing_cpp import safe_extract_context
from collections import Counter


PRIMITIVE_TYPES = {
    "bool", "char", "signed char", "unsigned char",
    "wchar_t", "char8_t", "char16_t", "char32_t",
    "int64_t", "int32_t", "int16_t", "int8_t",
    "__int64", "__int32", "__int16", "__int8",
    "short", "short int", "signed short", "signed short int", "unsigned short", "unsigned short int",
    "int", "signed", "signed int", "unsigned", "unsigned int",
    "long", "long int", "signed long", "signed long int", "unsigned long", "unsigned long int", 
    "long long", "long long int", "unsigned long long", "unsigned long long int",
    "float", "double", "long double", "void"
}
CONST_VOLATILE = re.compile(r'\b(const|volatile)\b')


def categorize_type_spelling(type_spelling : str | None) -> str:
    if not type_spelling:
        return "TYPE_UNKNOWN"

    s = CONST_VOLATILE.sub(" ", type_spelling).strip()
    if s.endswith(("&&", "&")):
        return "TYPE_REF"
    if "<" in s and ">" in s:
        return "TYPE_TEMPLATE"
    if "*" in s and "[" not in s and "(" not in s:
        return "TYPE_PTR"
    if "::" in s:
        return "TYPE_NAMESPACE"
    temp = s.split()
    if temp:
        base = temp[0]
        if base in PRIMITIVE_TYPES:
            return "TYPE_PRIMITIVE"
    return "TYPE_USER"


def cursor_core_features(cursor_core : dict ) -> tuple[list[str], dict[str, float]]:
    tokens = []
    numeric = {}
    if not cursor_core:
        return tokens, numeric

    kind = cursor_core.get("kind")
    if kind:
        tokens.append(f"CURSOR_KIND={kind}")

    # Бинарные признаки по is_decl/is_expr/is_stmt
    for flag_name in ("is_decl", "is_expr", "is_stmt"):
        flag = cursor_core.get(flag_name)
        numeric[flag_name.upper()] = 1.0 if flag else 0.0

    # Категория типа курсора
    t = cursor_core.get("type")
    type_cat = categorize_type_spelling(t)
    tokens.append(f"CURSOR_TYPE_CAT={type_cat}")

    return tokens, numeric


def cursor_meta_features(cursor_meta : dict) -> tuple[list[str], dict[str, float]]:
    tokens = []
    numeric = {}

    if not cursor_meta:
        return tokens, numeric

    # BINARY_OPERATOR
    op = cursor_meta.get("op_spelling")
    if op:
        tokens.append(f"BINOP_AT_ERROR={op}")
    lhs_type = cursor_meta.get("lhs_type")
    rhs_type = cursor_meta.get("rhs_type")
    if lhs_type:
        tokens.append(f"BINOP_LHS_CAT={categorize_type_spelling(lhs_type)}")
    if rhs_type:
        tokens.append(f"BINOP_RHS_CAT={categorize_type_spelling(rhs_type)}")

    # CALL_EXPR
    num_args = cursor_meta.get("num_args")
    if isinstance(num_args, int):
        numeric["N_ARGS"] = num_args

    arg_types = cursor_meta.get("arg_types") or []
    for i, t in enumerate(arg_types[:4]):
        tokens.append(f"CALL_ARG{i}_CAT={categorize_type_spelling(t)}")

    # Ссылки: DECL_REF_EXPR / MEMBER_REF_EXPR / TYPE_REF
    ref_kind = cursor_meta.get("ref_kind")
    if ref_kind:
        tokens.append(f"REF_KIND={ref_kind}")
    ref_type = cursor_meta.get("ref_type")
    if ref_type:
        tokens.append(f"REF_TYPE_CAT={categorize_type_spelling(ref_type)}")
    is_type_ref = cursor_meta.get("is_type_ref")
    numeric["IS_TYPE_REF"] = 1.0 if is_type_ref else 0.0
    return tokens, numeric


def build_global_features(ctx : dict) -> tuple[list[str], dict[str, float]]:
    tokens = []
    numeric = {}

    # --- 1. Локальные токены вокруг ошибки ---
    local_tokens_norm = ctx.get("local_tokens_norm") or []
    tokens.extend(local_tokens_norm)

    # --- 2. cursor_core / cursor_meta / parent_chain ---
    cursor_core = ctx.get("cursor_core") or {}
    cursor_meta = ctx.get("cursor_meta") or {}
    tokens_core, numeric_core = cursor_core_features(cursor_core)
    tokens_meta, numeric_meta = cursor_meta_features(cursor_meta)
    tokens.extend(tokens_core)
    tokens.extend(tokens_meta)
    numeric.update(numeric_core)
    numeric.update(numeric_meta)

    # parent_chain: кто над узлом
    # PARENT_0 = непосредственный родитель, PARENT_1 = дед и т.д.
    parent_chain = ctx.get("parent_chain") or []
    for depth, kind in enumerate(parent_chain):
        tokens.append(f"PARENT_{depth}={kind}")
    # простая числовая фича глубины
    numeric["PARENT_CHAIN_LEN"] = float(len(parent_chain))

    # --- 3. includes ---
    includes = ctx.get("includes") or []
    numeric["N_INCLUDES"] = float(len(includes))

    # можно добавить более грубые категории по имени заголовка
    IO_HEADERS = {"iostream", "iomanip", "cstdio", "stdio", "fstream", "sstream", "istream", "ostream", "ifstream", "ofstream"}
    CONTAINER_HEADERS = {"vector", "list", "forward_list", "deque", "map", "set", "unordered_map", "unordered_set", "queue", "stack", "array", "bitset"}
    ALG_HEADERS = {"algorithm", "numeric", "functional"}
    MATH_HEADERS = {"math", "cmath", "complex", "random"}
    STRING_HEADERS = {"string", "string_view", "cstring", "cwchar", "sstream", "streambuf", "regex"}
    THREAD_HEADERS = {"thread", "mutex", "condition_variable", "future"}

    for h in includes:
        base = h.split(".")[0]
        if base in IO_HEADERS:
            tokens.append("INC_CAT_IO")
        if base in CONTAINER_HEADERS:
            tokens.append("INC_CAT_CONTAINER")
        if base in ALG_HEADERS:
            tokens.append("INC_CAT_ALGO")
        if base in MATH_HEADERS:
            tokens.append("INC_CAT_MATH")
        if base in STRING_HEADERS:
            tokens.append("INC_CAT_STRING")
        if base in THREAD_HEADERS:
            tokens.append("INC_CAT_THREAD")

    # --- 4. Макросы и препроцессор ---
    macros = ctx.get("macros") or []
    n_macro_def = sum(1 for m in macros if m.get("kind") == "macro_def")
    n_macro_use = sum(1 for m in macros if m.get("kind") == "macro_use")
    n_pp_dir = sum(1 for m in macros if m.get("kind") == "pp_directive")

    numeric["N_MACRO_DEF"] = float(n_macro_def)
    numeric["N_MACRO_USE"] = float(n_macro_use)
    numeric["N_PP_DIRECTIVE"] = float(n_pp_dir)

    # --- 5. using / typedef / alias templates / namespaces ---
    aliases_ns = ctx.get("aliases_ns") or {}
    using_directives = aliases_ns.get("using_directives") or []
    using_decls = aliases_ns.get("using_decls") or []
    typedefs = aliases_ns.get("typedefs") or []
    namespaces = aliases_ns.get("namespaces") or []

    numeric["N_USING_DIRECTIVES"] = float(len(using_directives))
    numeric["N_USING_DECLS"] = float(len(using_decls))
    numeric["N_TYPEDEFS"] = float(len(typedefs))
    numeric["N_NAMESPACES"] = float(len(namespaces))

    # токены по using namespace X;
    for ns in using_directives:
        tokens.append(f"USING_NS={ns}")

    # typedef / using alias —
    for td in typedefs:
        underlying = td.get("underlying")
        cat = categorize_type_spelling(underlying)
        tokens.append(f"TYPEDEF_UNDER_CAT={cat}")

    # --- 6. Декларации типов/переменных/функций ---
    decls = ctx.get("decls") or {}
    types = decls.get("types") or []
    vars = decls.get("vars") or []
    funcs = decls.get("funcs") or []

    # счётчики по kinds
    type_kinds = Counter(t["kind"] for t in types)
    var_kinds = Counter(v["kind"] for v in vars)
    func_kinds = Counter(f["kind"] for f in funcs)

    for kind, cnt in type_kinds.items():
        numeric[f"N_TYPE_{kind}"] = float(cnt)
    for kind, cnt in var_kinds.items():
        numeric[f"N_VAR_{kind}"] = float(cnt)
    for kind, cnt in func_kinds.items():
        numeric[f"N_FUNC_{kind}"] = float(cnt)

    # грубые суммарные признаки
    numeric["N_TYPES_TOTAL"] = float(len(types))
    numeric["N_VARS_TOTAL"] = float(len(vars))
    numeric["N_FUNCS_TOTAL"] = float(len(funcs))

    # можно добавить токены, если есть структуры/классы/шаблоны
    has_struct = any(t["kind"] == "STRUCT_DECL" for t in types)
    has_class = any(t["kind"] == "CLASS_DECL" for t in types)
    has_enum = any(t["kind"] == "ENUM_DECL" for t in types)
    has_class_template = any(t["kind"] == "CLASS_TEMPLATE" for t in types)

    numeric["HAS_STRUCT"] = 1.0 if has_struct else 0.0
    numeric["HAS_CLASS"] = 1.0 if has_class else 0.0
    numeric["HAS_ENUM"] = 1.0 if has_enum else 0.0
    numeric["HAS_CLASS_TEMPLATE"] = 1.0 if has_class_template else 0.0

    # по vars — можно при желании грубо оценить «типовое разнообразие»
    var_type_cats = Counter(
        categorize_type_spelling(v.get("type")) for v in vars
    )
    for cat, cnt in var_type_cats.items():
        numeric[f"N_VARS_{cat}"] = float(cnt)
    return tokens, numeric


def normalize_source_code(source_code : str, error_line : int) -> tuple[list[str], dict[str, float]]:
    ctx = safe_extract_context(source_code, error_line)
    tokens, numeric = build_global_features(ctx)
    return tokens, numeric


TOKEN_RE = re.compile(
    r"<[A-Z0-9_]+>|C\d{4}|[A-Za-zА-Яа-яЁё0-9_]+",
    re.VERBOSE
)

def normalize_error_text(error_text : str) -> str:
    res = ""
    error_code = error_text[:5]
    match error_code:
        case 'C2065':
            res = re.sub(r': ([^:]+):', ': <IDENT>', error_text, count=1)
        case 'C3861' | 'C2672':
            res = re.sub(r': ([^:]+):', ': <FUNC>', error_text, count=1)
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
            res = re.sub(r'"[^"]+"', '<INDENT>', error_text, count=1)
        case 'C1075':
            res = re.sub(r'"\{"', '<BRACE>', error_text, count=1)
        case 'C2131' | 'C2148' | 'C2181':
            pass
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


def error_tokenizer(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def test_normalize_source_code() -> None:
    source_code = """
        #include <stdio.h>
        #include<string>
        #include<string.h>
        #include <math.h>
        #include<iostream>
        #include <algorithm>
        #include <map>
        #include <vector>
        #include <queue>
        using namespace std;




        #define MyAbs(a) ((a)>0?(a):-(a))
        #define MyEqualDoule(a,b) (MyAbs(a-b)<1e-6)

        void init()
        {
        #ifdef _WIN32
                freopen("1.txt", "r", stdin);
        #endif
        }

        void func();

        int main()
        {
                init();
                func();

                return 0;
        }


        void func()
        {
                double a,b,c,d,e,f, x, y;
                while(~scanf("%lf%lf%lf%lf%lf%lf", &a, &b, &c, &d, &e, &f))
                {
                        if(MyEqualDoule(a*e-b*d,0))
                                x = 0;
                        else
                                x = (c*e-f*b)/(a*e - b*d);

                        if(MyEqualDoule(b*d - a*e),0)
                                y = 0;
                        else
                                y = (c*d-a*f)/(b*d - a*e);
                        printf("%.3lf %.3lf
        ", x, y);
                }
        }
    """
    res1, res2 = normalize_source_code(source_code, 46)
    print(res1, end='\n\n')
    print(res2)


def test_normalize_error_code() -> None:
    error_text = input()
    temp = normalize_error_text(error_text)
    res = error_tokenizer(temp)
    print(temp, res, sep="\n")


if __name__ == "__main__":
    # test_normalize_source_code()
    test_normalize_error_code()