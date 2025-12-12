# pyright: reportAttributeAccessIssue=none
import os, json, time
from clang import cindex
from clang.cindex import TranslationUnit, CursorKind, Cursor, TokenKind, Token
from collections import defaultdict, Counter
from .compile_cpp import normalize_includes
from config import TEMP_OUTPUT_DIR


FILE_NAME = "code.cpp"
INDEX = cindex.Index.create()
OPERATORS = {
    "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!",
    "+", "-", "*", "/", "%", "++", "--",
    "=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "&", "|", "^", "~", "<<", ">>", "<<=", ">>=",
    ".", "->", "?", ":", ","
}
INTERESTING_KINDS = {
        # выражения с типами и операндами
        CursorKind.BINARY_OPERATOR,
        CursorKind.UNARY_OPERATOR,
        CursorKind.CALL_EXPR,
        CursorKind.DECL_REF_EXPR,
        CursorKind.MEMBER_REF_EXPR,
        CursorKind.TYPE_REF,
        # локальные операторы управления потоком
        CursorKind.RETURN_STMT,
        CursorKind.IF_STMT,
        CursorKind.FOR_STMT,
        CursorKind.WHILE_STMT,
        CursorKind.SWITCH_STMT,
        # объявления, которые часто попадают на строку ошибки
        CursorKind.VAR_DECL,
        CursorKind.PARM_DECL,
        CursorKind.FIELD_DECL,
        CursorKind.FUNCTION_DECL,
        CursorKind.CXX_METHOD,
    }
INCLUDE_ENV = os.environ.get("INCLUDE", "")
INCLUDE_ARGS = [
    "-I" + p.strip()
    for p in INCLUDE_ENV.split(";")
    if p.strip()
]
CLANG_ARGS = [
    "-std=c++14",
    "-x", "c++",
    "-fms-compatibility",
    "-fms-extensions",
    "-fdelayed-template-parsing",
    *INCLUDE_ARGS
]

class TUIndex:
    def __init__(self) -> None:
        self.cursors_by_line = defaultdict(list)
        self.using_directives = []
        self.using_decls = []
        self.typedefs = []
        self.namespaces = []
        self.type_kind_counts = Counter()
        self.var_kind_counts = Counter()
        self.var_type_counts = Counter()
        self.func_kind_counts = Counter()
        self.includes = []
        self.macros = []
        self.macro_defs = set()
        self.macro_uses = set()
        self.parent = {}


def parse(source_code : str, with_macros : bool) -> TranslationUnit:
    if with_macros:
        options = TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    else:
        options = 0
    tu = INDEX.parse(FILE_NAME, args=CLANG_ARGS,
                 unsaved_files=[(FILE_NAME, source_code)],
                 options=options)
    return tu


def build_tu_index(tu : TranslationUnit, with_macros : bool) -> TUIndex:
    idx = TUIndex()

    def visit(cur : Cursor, parent : Cursor | None) -> None:
        loc = cur.location
        if not loc.file:
            for child in cur.get_children():
                visit(child, cur)
            return
        if loc.file.name != FILE_NAME:
            return
        
        idx.parent[cur.hash] = parent
        k = cur.kind
        if k in INTERESTING_KINDS:
            line = cur.location.line
            idx.cursors_by_line[line].append(cur)

        # макросы
        if with_macros:
            if k == CursorKind.MACRO_DEFINITION:
                name = cur.spelling
                idx.macros.append({
                    "kind": "macro_def",
                    "name": name,
                    "line": cur.location.line,
                })
                idx.macro_defs.add(name)
            elif k == CursorKind.MACRO_INSTANTIATION:
                name = cur.spelling
                idx.macros.append({
                    "kind": "macro_use",
                    "name": name,
                    "line": cur.location.line,
                })
                idx.macro_uses.add(name)
            elif k == CursorKind.PREPROCESSING_DIRECTIVE:
                idx.macros.append({
                    "kind": "pp_directive",
                    "spelling": cur.spelling,
                    "line": cur.location.line,
                })
        
        # using / typedef / namespace
        if k == CursorKind.USING_DIRECTIVE:
            ref = cur.get_definition() or cur.referenced
            if ref is not None:
                name = ref.displayname or ref.spelling
            else:
                name = "<UNKNOWN_NS>"
            idx.using_directives.append(name)
        elif k == CursorKind.USING_DECLARATION:
            idx.using_decls.append(cur.spelling)
        elif k in {CursorKind.TYPEDEF_DECL, CursorKind.TYPE_ALIAS_DECL}:
            try:
                ut = cur.underlying_typedef_type
                underlying_spelling = ut.spelling
            except Exception:
                underlying_spelling = cur.type.get_canonical().spelling
            idx.typedefs.append({
                "name": cur.spelling,
                "underlying": underlying_spelling,
                "kind": k.name
            })
        elif k == CursorKind.NAMESPACE:
            idx.namespaces.append(cur.spelling)

        # decls
        if k in {CursorKind.STRUCT_DECL, CursorKind.CLASS_DECL, CursorKind.UNION_DECL, CursorKind.ENUM_DECL, CursorKind.CLASS_TEMPLATE}:
            idx.type_kind_counts[k.name] += 1
        elif k in {CursorKind.VAR_DECL, CursorKind.FIELD_DECL, CursorKind.PARM_DECL}:
            t_sp = cur.type.spelling
            idx.var_kind_counts[k.name] += 1
            idx.var_type_counts[t_sp] += 1
        elif k in {CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD, CursorKind.CONSTRUCTOR, CursorKind.DESTRUCTOR, CursorKind.FUNCTION_TEMPLATE}:
            idx.func_kind_counts[k.name] += 1

        for child in cur.get_children():
            visit(child, cur)
    
    visit(tu.cursor, None)

    # includes
    for inc in tu.get_includes():
        if inc.is_input_file:
            continue
        if not inc.location.file or inc.location.file.name != FILE_NAME:
            continue
        if inc.depth != 1:
            continue
        idx.includes.append(os.path.basename(inc.include.name))
    return idx


def get_operator_spelling(cur : Cursor) -> str | None:
    tu = cur.translation_unit
    for tok in tu.get_tokens(extent=cur.extent):
        if tok.kind == TokenKind.PUNCTUATION and tok.spelling in OPERATORS:
            return tok.spelling
    return None


def find_smallest_cursor_by_line(idx : TUIndex, line : int) -> Cursor | None:
    candidates = idx.cursors_by_line.get(line, [])
    if not candidates:
        return None
    
    best = None
    best_len = None

    for cur in candidates:
        r = cur.extent
        if not (r.start.line <= line <= r.end.line):
            continue

        length = r.end.offset - r.start.offset
        if best is None or length < best_len:
            best = cur
            best_len = length

    return best


def get_tokens_around_line(tu : TranslationUnit, line : int, radius : int = 2) -> list[Token]:
    lo = max(1, line - radius)
    hi = line + radius
    file = tu.get_file(FILE_NAME)
    start = cindex.SourceLocation.from_position(tu, file, lo, 1)
    end = cindex.SourceLocation.from_position(tu, file, hi + 1, 1)
    extent = cindex.SourceRange.from_locations(start, end)
    tokens = list(tu.get_tokens(extent=extent))
    return tokens


def get_parent_chain(cur : Cursor | None, idx : TUIndex, max_depth : int = 6) -> list[str]:
    chain = []
    if cur is None:
        return chain

    node = cur
    depth = 0
    while depth < max_depth:
        parent = idx.parent.get(node.hash)
        if parent is None:
            break
        if parent.kind == CursorKind.TRANSLATION_UNIT:
            break
        chain.append(parent.kind.name)
        node = parent
        depth += 1
    return chain


def normalize_token(tok : Token, idx : TUIndex, with_macros : bool) -> str:
    cur = tok.cursor
    spelling = tok.spelling
    tk = tok.kind
    
    def liter(spelling : str) -> str:
        if spelling.replace('.', '', 1).lstrip('+-').isdigit():
            return "<NUM>"
        return "<STR>"
    
    if cur is None:
        if tk == TokenKind.IDENTIFIER:
            if spelling in idx.macro_uses:
                return "<MACRO_NAME_USE>"
            if spelling in idx.macro_defs:
                return "<MACRO_NAME_DEF>"
            return "<ID_IDENT>"
        
        if tk == TokenKind.LITERAL:
            return liter(spelling)
        if tk == TokenKind.PUNCTUATION:
            if spelling in OPERATORS:
                return "OP_" + spelling
            return spelling
        
        if tk == TokenKind.KEYWORD:
            return spelling.upper()
        return spelling
    
    k = cur.kind
    if with_macros:
        loc = tok.location
        start = cur.extent.start
        if k == CursorKind.INCLUSION_DIRECTIVE:
            if loc.line == start.line and loc.column == start.column:
                return "<PP_INCLUDE>"
            return ""
        
        if k == CursorKind.PREPROCESSING_DIRECTIVE:
            if loc.line != start.line or loc.column != start.column:
                return ""
            text = (cur.spelling or "").lstrip()
            if text.startswith("define"):
                return "<PP_DEFINE>"
            if text.startswith("pragma"):
                return "<PP_PRAGMA>"
            if text.startswith(("if", "#ifdef", "#ifndef")):
                return "<PP_IF>"
            if text.startswith("elif"):
                return "<PP_ELIF>"
            if text.startswith("else"):
                return "<PP_ELSE>"
            if text.startswith("endif"):
                return "<PP_ENDIF>"
            return "<PP_OTHER>"
    
        if k == CursorKind.MACRO_DEFINITION:
            return "<MACRO_DEF>"
        if k == CursorKind.MACRO_INSTANTIATION:
            return "<MACRO_USE>"

    if tk == TokenKind.LITERAL:
        return liter(spelling)
    if tk == TokenKind.IDENTIFIER:
        t = cur.type
        ref = getattr(cur, "referenced", None)
        if with_macros:
            if spelling in idx.macro_uses:
                return "<MACRO_NAME_USE>"
            if spelling in idx.macro_defs:
                return "<MACRO_NAME_DEF>"
        if k in {CursorKind.TYPEDEF_DECL, CursorKind.TYPE_ALIAS_DECL}:
            return "<ID_TYPE_ALIAS_DECL>"
        
        if k == CursorKind.TYPE_REF:
            if ref and ref.kind in {CursorKind.TYPEDEF_DECL, CursorKind.TYPE_ALIAS_DECL, CursorKind.TYPE_ALIAS_TEMPLATE_DECL}:
                return "<ID_TYPE_ALIAS_USE>"
            if ref and ref.location.file and ref.location.file.name == FILE_NAME:
                return "<ID_TYPE_USER_USE>"
            return "<ID_TYPE_BUILTIN_USE>"
        
        if k in {CursorKind.VAR_DECL, CursorKind.PARM_DECL, CursorKind.FIELD_DECL}:
            if t.kind.spelling.startswith("Pointer"):
                return "<ID_VAR_PTR_DECL>"
            if t.kind.spelling.startswith("Record"):
                return "<ID_VAR_OBJ_DECL>"
            return "<ID_VAR_SCALAR_DECL>"
        
        if k == CursorKind.DECL_REF_EXPR and ref:
            if ref.kind in {CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD, CursorKind.CONSTRUCTOR, CursorKind.DESTRUCTOR, CursorKind.FUNCTION_TEMPLATE}:
                if ref.location.file and ref.location.file.name == FILE_NAME:
                    return "<ID_FUNC_USE_USER>"
                return "<ID_FUNC_USE_LIB>"
            
            if ref.kind in {CursorKind.VAR_DECL, CursorKind.PARM_DECL, CursorKind.FIELD_DECL}:
                rt = ref.type
                if rt.kind.spelling.startswith("Pointer"):
                    return "<ID_VAR_PTR_USE>"
                if rt.kind.spelling.startswith("Record"):
                    return "<ID_VAR_OBJ_USE>"
                return "<ID_VAR_SCALAR_USE>"

        if k in {CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD, CursorKind.CONSTRUCTOR, CursorKind.DESTRUCTOR, CursorKind.FUNCTION_TEMPLATE}:
            return "<ID_FUNC_DECL>"
        return "<ID_IDENT>"

    if tk == TokenKind.PUNCTUATION:
        if spelling in OPERATORS:
            return "OP_" + spelling
        return spelling
    
    if tk == TokenKind.KEYWORD:
        return spelling.upper()
    return spelling


def extract_cursor_core_info(cur : Cursor | None) -> dict[str, str | bool | int | None]:
    if cur is None:
        return {}
    
    info = {
        "kind": cur.kind.name,
        "spelling": cur.spelling,
        "displayname": cur.displayname,
        "line": cur.location.line,
        "is_decl": cur.kind.is_declaration(),
        "is_expr": cur.kind.is_expression(),
        "is_stmt": cur.kind.is_statement(),
    }
    if cur.type.kind.value != 0:
        info["type"] = cur.type.spelling
    if hasattr(cur, "result_type"):
        info["result_type"] = cur.result_type.spelling
    return info


def extract_cursor_meta(cur : Cursor | None) -> dict[str, str | int | bool | list[str] | None]:
    if cur is None:
        return {}
    
    info = {}
    if cur.kind == CursorKind.BINARY_OPERATOR:
        children = [c for c in cur.get_children()]
        lhs, rhs = (children + [None, None])[:2]
        op_spelling = get_operator_spelling(cur)
        if op_spelling:
            info["op_spelling"] = op_spelling
        if lhs.type.spelling:
            info["lhs_type"] = lhs.type.spelling
        if rhs.type.spelling:
            info["rhs_type"] = rhs.type.spelling
        if lhs.kind.name:
            info["lhs_kind"] = lhs.kind.name
        if rhs.kind.name:
            info["rhs_kind"] = rhs.kind.name
    if cur.kind == CursorKind.CALL_EXPR:
        args = list(cur.get_arguments())
        info["num_args"] = len(args)
        if args:
            info["arg_types"] = [a.type.spelling for a in args]
        if cur.result_type.spelling:
            info["result_type"] = cur.result_type.spelling
    if cur.kind in {CursorKind.DECL_REF_EXPR, CursorKind.MEMBER_REF_EXPR, CursorKind.TYPE_REF}:
        ref = cur.referenced
        info["is_type_ref"] = (cur.kind == CursorKind.TYPE_REF)
        if ref.kind.name:
            info["ref_kind"] = ref.kind.name
        if ref.type.spelling:
            info["ref_type"] = ref.type.spelling
    return info


def extract_error_context(tu : TranslationUnit, idx : TUIndex, line : int, with_macros : bool, radius : int = 2) -> dict[str, int | list | dict]:
    # 1. Локальный AST-узел: без column, только по строке
    error_cursor = find_smallest_cursor_by_line(idx, line)
    core_info = extract_cursor_core_info(error_cursor)

    # 2. Метаинформация по узлу + цепочка родителей
    cursor_meta = extract_cursor_meta(error_cursor)
    parent_chain = get_parent_chain(error_cursor, idx, 6)

    # 3. Локальные токены и их нормализация
    local_tokens = get_tokens_around_line(tu, line, radius=radius)
    local_tokens_norm = [nt for nt in (normalize_token(t, idx, with_macros) for t in local_tokens) if nt]

    # 4. Глобальные признаки по файлу
    includes = idx.includes
    macros = idx.macros

    aliases_ns = {}
    if idx.using_directives:
        aliases_ns["using_directives"] = idx.using_directives
    if idx.using_decls:
        aliases_ns["using_decls"] = idx.using_decls
    if idx.typedefs:
        aliases_ns["typedefs"] = idx.typedefs
    if idx.namespaces:
        aliases_ns["namespaces"] = idx.namespaces
    
    decls = {}
    if idx.type_kind_counts:
        decls["type_kind_counts"] = dict(idx.type_kind_counts)
    if idx.var_kind_counts:
        decls["var_kind_counts"] = dict(idx.var_kind_counts)
    if idx.var_type_counts:
        decls["var_type_counts"] = dict(idx.var_type_counts)
    if idx.func_kind_counts:
        decls["func_kind_counts"] = dict(idx.func_kind_counts)

    res = {"line": line}
    if core_info:
        res["core_info"] = core_info # type: ignore
    if cursor_meta:
        res["cursor_meta"] = cursor_meta # type: ignore
    if parent_chain:
        res["parent_chain"] = parent_chain # type: ignore
    if local_tokens_norm:
        res["local_tokens_norm"] = local_tokens_norm # type: ignore
    if includes:
        res["includes"] = includes # type: ignore
    if macros:
        res["macros"] = macros # type: ignore
    if aliases_ns:
        res["aliases_ns"] = aliases_ns # type: ignore
    if decls:
        res["decls"] = decls # type: ignore
    return res # type: ignore


def safe_extract_context(source_code : str, error_line : int, with_macros : bool, radius : int = 2) -> dict[str, int | str | list | dict]:
    try:
        tu = parse(source_code, with_macros)
    except Exception as e:
        print(f"error: parse_failed: {e}, line: {error_line}")
        return {}
    try:
        idx = build_tu_index(tu, with_macros)
    except Exception as e:
        print(f"error: index_failed: {e}, line: {error_line}")
        return {}
    try:
        return extract_error_context(tu, idx, error_line, with_macros, radius) # type: ignore
    except Exception as e:
        print(f"error: extract_failed: {e}, line: {error_line}")
        return {}
    

def main() -> None:
    source_code = """
        #include <bits/stdc++.h>
        
        using namespace std;
        #define rep(i,n) for(int i=0; i<(n); i++)
        using ll = long long;
        using P = pair<int,int>;
        const int INF = 1001001001;
        int main()
        {
            int h,n;
            cin >> h >> n;
            vector<int> dp(h+1,INF);
            dp[h] = 0;
            rep(i,n){
                int a,b;
                cin >> a >> b;
                for(int j = h;j>=0;--j){
                
                    dp[max(j-a,0)] = min(dp[j]+b,dp[max(j-a,0)]);
                }
            }
            cout << dp[0] << endl;

            return 0;
        （
    """
    error_line = 83

    source_code = normalize_includes(source_code)
        
    t0 = time.perf_counter()
    tu = parse(source_code, False)
    t1 = time.perf_counter()

    idx = build_tu_index(tu, False)
    t2 = time.perf_counter()

    res = extract_error_context(tu, idx, error_line, False, radius=2)
    t3 = time.perf_counter()

    print("parse:", t1 - t0, "sec")
    print("build_tu_index:", t2 - t1, "sec")
    print("extract_error_context:", t3 - t2, "sec")
    print(f"total: {t3-t0}")

    # res = safe_extract_context(source_code, error_line, True, 2)

    with open(TEMP_OUTPUT_DIR / "output_new.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()