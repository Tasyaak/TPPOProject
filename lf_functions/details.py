import re, difflib
from pandas import Series


CPP_KEYWORDS = {
    "if", "else", "switch", "case", "default",
    "for", "while", "do", "break", "continue", "goto", "return",
    "bool", "char", "wchar_t", "char8_t", "char16_t", "char32_t",
    "int64_t", "int32_t", "int16_t", "int8_t",
    "__int64", "__int32", "__int16", "__int8",
    "short", "int", "signed", "unsigned", "long",
    "float", "double", "void",
    "true", "false", "nullptr",
    "class", "struct", "union", "enum",
    "vector", "list", "forward_list", "deque", "map", "set", "unordered_map",
    "unordered_set", "queue", "stack", "array", "bitset", "pair",
    "public", "protected", "private",
    "friend", "virtual", "explicit", "mutable",
    "namespace",
    "template", "typename", "typedef", "using",
    "new", "delete", "operator", "sizeof","this",
    "const", "constexconstexpr", "consteval", "constinit", "volatile",
    "static", "extern", "register", "thread_local", "inline",
    "noexcept",
    "static_cast", "const_cast", "reinterpret_cast",
    "try", "catch", "throw",
    "and", "or", "not", "xor",
    "bitand", "bitor", "compl",
    "and_eq", "or_eq", "xor_eq", "not_eq",
    "decltype", "typeid",
    "static_assert",
    "cout", "cin", "cerr", "clog", "wcout", "wcin", "wcerr", "wclog",
}
CPP_FUNCTIONS = {
    "abort", "abs", "accumulate", "acos", "acosh", "addressof", "adjacent_difference", "advance",
    "all_of", "allocate_shared", "any_of", "append", "asctime", "asin", "asinh", "assert",
    "atan", "atanh", "atanl", "atanf", "atan2", "atan2l", "atan2f" "atof", "atoi", "atol",
    "back", "bsearch", "bucket", "bucket_count", "calloc", "capacity", "cbegin", "cbrt", "ceil",
    "cend", "clear", "clock", "compare", "copy", "copy_if", "copy_n", "copysign", "count", "count_if",
    "c_str", "ctime", "dec", "defaultfloat", "difftime", "distance", "dynamic_pointer_cast", "empty", "endl",
    "ends", "erase", "erf", "erfc", "exit", "exp", "exp2", "expm1", "fabs", "fclose", "fdim", "fgets", "fill", "fflush",
    "floor", "flush", "fmod", "fopen", "fprintf", "fputs", "fread", "free", "freopen", "frexp", "front", "fscanf",
    "fseek", "ftell", "fwrite", "gcd", "get", "gets", "getchar", "getline", "gmtime", "hash", "hex", "hexfloat", "hypot", "ignore",
    "inner_product", "insert", "internal", "iota", "isfinite", "isgreater", "isgreaterequal", "isinf", "isless",
    "islessequal", "islessgreater", "isnan", "isnormal", "isunordered", "is_heap", "is_heap_until", "is_partitioned",
    "is_sorted", "is_sorted_until", "istream_iterator", "lalpha", "ldexp", "length", "lgamma", "llround", "load_factor",
    "localtime", "log", "log10", "log1p", "log2", "lround", "malloc", "make_error_code", "make_error_condition", "make_heap",
    "make_pair", "make_shared", "make_tuple", "make_unique", "max", "max_size", "memcmp", "memcpy", "memmove", "memset", "merge",
    "min", "mismatch", "modf", "move", "move_backward", "next", "nextafter", "next_permutation", "nexttoward", "none_of",
    "noshowbase", "noshowpoint", "noshowpos", "noboolalpha", "oct", "partial_sort", "partial_sort_copy", "partial_sum", "perror",
    "pop", "pop_back", "pop_front", "pop_heap", "pow", "printf", "push", "push_back", "push_front", "push_heap", "puts", "qsort",
    "rbegin", "read", "realloc", "ref", "rehash", "remquo", "remove", "remove_copy", "remove_copy_if", "remove_if", "replace",
    "replace_copy", "replace_copy_if", "replace_if", "reserve", "reset", "resize", "return_temporary_buffer", "rethrow_exception",
    "rewind", "right", "rfind", "rotate", "rotate_copy", "round", "rtrim", "scientific", "search", "search_n", "set_difference",
    "set_intersection", "set_symmetric_difference", "set_union", "setfill", "setprecision", "setw", "shrink_to_fit", "shuffle",
    "signbit", "sin", "sinh", "size", "sort", "sort_heap", "sprintf", "sqrt", "scanf", "sscanf", "stable_partition", "stable_sort",
    "static_pointer_cast", "stoi", "stol", "stold", "stoll", "stof", "stod", "stoull", "stoul", "strat", "strcat", "strchr",
    "strcmp", "strcpy", "strcspn", "strlen", "strncat", "strncmp", "strncpy", "strpbrk", "strrchr", "strspn", "strstr", "strtok",
    "substr", "swap", "swap_ranges", "system", "tan", "tanh", "tgamma", "time", "tie", "top", "to_string", "transform", "trunc",
    "type_index", "ungetc", "unique", "unique_copy", "unique_lock", "unordered_map", "unordered_set", "upper_bound", "value",
    "vprintf", "vsnprintf", "wait", "wait_for", "wait_until", "write", "ws", "yield",
}
KNOWN_STD_IDENTIFIERS_FOR_HEADER = {
    "cout", "cin", "cerr", "clog", "wcout", "wcin", "wcerr", "wclog",
    "string", "wstring", "vector", "list", "forward_list", "deque", "map", "set", "unordered_map",
    "unordered_set", "queue", "stack", "array", "bitset", "pair",
    "ifstream", "ofstream", "fstream", "istringstream", "ostringstream", "stringstream",
    "abs", "sqrt", "sin", "cos", "tan", "log", "log10", "exp", "pow", "ceil", "floor", "round", "trunc",
    "printf", "scanf", "puts", "gets", "strlen", "strcmp", "strcpy", "memset", "memcpy",
    "system", "count", "sort", "max", "min", "M_PI", "M_PI_2",
}
TYPE_KEYWORDS = {
    "bool", "char", "wchar_t", "char8_t", "char16_t", "char32_t",
    "int64_t", "int32_t", "int16_t", "int8_t",
    "__int64", "__int32", "__int16", "__int8",
    "short", "int", "signed", "unsigned", "long",
    "float", "double", "void", "string", "wstring",
    "vector", "list", "forward_list", "deque", "map", "set", "unordered_map",
    "unordered_set", "queue", "stack", "array", "bitset", "pair"
}
COMMON_TYPE_ALIASES = { "ll", "ull" }
STREAM_OBJS = { "cin", "cout", "cerr", "clog", "wcin", "wcout", "wcerr", "wclog" }
CONTROL_KEYWORDS = { "return", "break", "continue", "else", "case" }
LOOP_KEYWORDS = { "for", "while", "switch" }

IDENT_RE_IN_ERROR_TEXT = re.compile(r"^C\d{4}: ([^:]+):")

def extract_ident(error_text : str) -> str | None:
    if not isinstance(error_text, str):
        return None
    m = IDENT_RE_IN_ERROR_TEXT.match(error_text)
    if not m:
        return None
    return m.group(1).strip()


def extract_line_concat(src : str, error_line : int) -> str:
    lines = src.split('\n')
    if 2 <= error_line:
        start = error_line - 2
    else:
        start = error_line - 1
    if error_line <= len(lines) - 1:
        end = error_line + 1
    else:
        end = error_line
    return "".join(lines[start:end])


def extract_lines(src : str, error_line : int) -> list[str]:
    lines = src.split('\n')
    if 2 <= error_line:
        start = error_line - 2
    else:
        start = error_line - 1
    if error_line <= len(lines) - 1:
        end = error_line + 1
    else:
        end = error_line
    return lines[start:end]


def pick_focus_line(window_lines : list[str], ident_err : str | None) -> str:
    if ident_err:
        pat = re.compile(rf"\b{re.escape(ident_err)}\b")
        for ln in window_lines:
            if pat.search(ln):
                return ln
    return window_lines[len(window_lines)//2] if window_lines else ""


IDENT_IN_CODE_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")

def extract_identifier_candidates(source_code : str, error_line : int | None = None, window : int = 10) -> set[str]:
    """
    Возвращает множество кандидатных идентификаторов из окна вокруг error_line
    """
    if not isinstance(source_code, str):
        return set()

    text = source_code.replace("\\n", "\n")
    lines = text.split("\n")

    if error_line is None or error_line <= 0 or error_line > len(lines):
        # если что-то не так, берём весь файл
        relevant_lines = lines
    else:
        start = max(0, error_line - 1 - window)
        end = min(len(lines), error_line + window)
        relevant_lines = lines[start:end]

    candidates = set()

    for line in relevant_lines:
        for match in IDENT_IN_CODE_RE.finditer(line):
            ident = match.group(0)
            # игнорируем ключевые слова
            if ident in CPP_KEYWORDS:
                continue
            candidates.add(ident)
    return candidates


CALL_RE_IN_CODE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")

def extract_function_candidates(source_code : str, error_line : int | None = None, window : int = 10) -> set[str]:
    if not isinstance(source_code, str):
        return set()

    text = source_code.replace("\\n", "\n")
    lines = text.split("\n")

    if error_line is None or error_line <= 0 or error_line > len(lines):
        relevant_lines = lines
    else:
        start = max(0, error_line - 1 - window)
        end = min(len(lines), error_line - 1 + window + 1)
        relevant_lines = lines[start:end]

    candidates = set()

    for line in relevant_lines:
        for m in CALL_RE_IN_CODE.finditer(line):
            name = m.group(1)
            if name in CPP_FUNCTIONS:
                continue
            candidates.add(name)
    return candidates


def find_best_match(id_err : str, candidates : set[str], cutoff : float = 0.8) -> str | None:
    """
    Возвращает лучший кандидат, похожий на id_err, или None.
    cutoff — минимальное значение similarity (0..1).
    """
    if not candidates:
        return None

    # difflib.SequenceMatcher.ratio ∈ [0, 1]
    best = None
    best_score = 0.0

    for cand in candidates:
        score = difflib.SequenceMatcher(None, id_err, cand).ratio()
        # слегка усилим значение, если совпадает первый символ и/или длина близка
        if cand and id_err and cand[0].lower() == id_err[0].lower():
            score += 0.05
        if abs(len(cand) - len(id_err)) <= 1:
            score += 0.05

        if score > best_score:
            best_score = score
            best = cand

    if best is not None and best_score >= cutoff:
        return best
    return None


def is_type_like_context(line : str, ident : str) -> bool:
    namespace_part = r'(?:[A-Za-z_]\w*::)*'
    template_part = r'(?:<[^<>]*>)?'  

    full_type = rf'{namespace_part}{re.escape(ident)}{template_part}'

    pattern_decl = rf"""
        (?:^|[;{{}}(])
        \s*
        (?:(?:constexpr|const)\s+)?
        {full_type}
        \s*
        (?:[\*&]+)?
        \s+
        (?P<name>[A-Za-z_]\w*)
    """
    m = re.search(pattern_decl, line, re.VERBOSE)
    if m:
        var_name = m.group('name')
        if var_name not in CPP_KEYWORDS:
            return True
        return False
    
    pattern_template = rf"""
        <(?![=<])
        [^>]*\b{re.escape(ident)}\b[^>]*>
    """
    if re.search(pattern_template, line, re.VERBOSE):
        return True
    return False


def is_control_like_context(line: str, ident: str) -> bool:
    pattern = rf"""
        (?:^|[;:{{}}\)])
        \s*
        {re.escape(ident)}
        \b
    """
    return re.search(pattern, line, re.VERBOSE) is not None


def is_loop_like_context(line: str, ident: str) -> bool:
    pattern = rf"""
            (?:^|[;:{{}}\)])
            \s*
            {re.escape(ident)}
            \s*
            \(
        """
    return re.search(pattern, line, re.VERBOSE) is not None


def is_keyword_typo(ident : str, kw : str | None, score : float) -> bool:
    if kw is None:
        return False
    L = max(len(ident), len(kw))
    if L <= 3:
        return score >= 0.66
    if L <= 5:
        return score >= 0.75
    return score >= 0.8


C2146_IDENT_QUOTED_RE = re.compile(
    r'(?:перед\s+идентификатором|before\s+identifier)\s*[\'"“”]([^\'"“”]+)[\'"“”]',
    re.IGNORECASE
)

def extract_ident_c2146(error_text : str) -> str | None:
    if not isinstance(error_text, str):
        return None
    m = C2146_IDENT_QUOTED_RE.search(error_text)
    return m.group(1).strip() if m else None


FOR_HEADER_RE = re.compile(r'\bfor\s*\((?P<body>[^)]*)\)')
ID = r"[A-Za-z_]\w*"
QUAL_TYPE = r"(?:[A-Za-z_]\w*::)*[A-Za-z_]\w*(?:<[^;(){}]*>)?"
RANGE_FOR_RE = re.compile(rf"""
                            ^\s*
                            (?P<decl>
                                (?:(?:const|volatile|constexpr)\s+)*
                                (?:auto|{QUAL_TYPE})
                                (?:\s*[\*&]\s*)*
                                (?:\[[^\]]+\]|{ID})
                            )
                            \s*(?<!:):(?!:)\s*
                            (?P<expr>.+?)\s*$
                            """, re.VERBOSE)

def is_range_for_body(body : str) -> bool:
    if ";" in body:
        return False
    return RANGE_FOR_RE.match(body) is not None


def for_header_missing_semicolon(line : str) -> bool:
    m = FOR_HEADER_RE.search(line)
    if not m:
        return False
    body = m.group("body")
    if not is_range_for_body(body) and body.count(";") < 2:
        return True
    return False


NUM_LIT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?:[uUlLfF]*)"
STR = r'"([^"\\]|\\.)*"'
CHR = r"'([^'\\]|\\.)*'"
STREAM_HEAD_RE = r"(?:std::\s*)?(?:w?cin|w?cout|w?cerr|w?clog)"
STREAM_MISSING_FIRST_OP_RE = re.compile(rf"""
                                        \b{STREAM_HEAD_RE}\b
                                        (?!\s*(?:<<|>>))
                                        \s+
                                        (?:{ID}|{NUM_LIT}|{STR}|{CHR})
                                        \s*(?:<<|>>)
                                        """, re.VERBOSE)
STREAM_MISSING_MID_OP_RE = re.compile(rf"""
                                        \b{STREAM_HEAD_RE}\b[^\n;]*?(?:<<|>>)\s*{ID}\s+{ID}\b
                                        """, re.VERBOSE)
STREAM_LIT_GLUE_RE = re.compile(rf"""
                                \b{STREAM_HEAD_RE}\b[^\n;]*?(?:<<|>>)\s*(?:{STR}|{CHR})\s*(?P<id>{ID})\b
                                """, re.VERBOSE)
SHIFT_OP_AFTER_RE = re.compile(r"^[ \t]*(?:<<|>>)")

def stream_missing_shift(line : str) -> bool:
    if not isinstance(line, str):
        return False

    # 1) cin a>>b / cout a<<b
    if STREAM_MISSING_FIRST_OP_RE.search(line):
        return True

    # 2) cin >> a b / cout << l m
    if STREAM_MISSING_MID_OP_RE.search(line):
        return True

    # 3) <<"="c и т.п., но не ловим "пропущенную ; перед cout"
    m = STREAM_LIT_GLUE_RE.search(line)
    if not m:
        return False

    ident2 = m.group("id")
    tail = line[m.end():]

    # фильтр от случая: cout<<"*"  cout<<...
    if ident2 in STREAM_OBJS and SHIFT_OP_AFTER_RE.match(tail):
        return False
    return True


NUM = r"(?:\d+(?:\.\d*)?|\.\d+)"
OPERAND = rf"(?:{ID}|{NUM}|{STR}|{CHR}|\]|\))"
ADJ_OPERANDS_WS_RE = re.compile(rf"""
                                (?P<left>{OPERAND})
                                \s+
                                (?P<right>{ID})
                                """, re.VERBOSE)
LIT_IDENT_GLUE_RE = re.compile(rf"""
                                (?P<lit>{STR}|{CHR})
                                \s*
                                (?P<right>{ID})
                                """, re.VERBOSE)
CALL_ARGS_RE = re.compile(rf"""
                            \b(?P<fname>{ID})\s*\((?P<args>[^()]*)\)
                            """, re.VERBOSE)

def missing_sep_in_call_args(line : str, ident_err : str | None) -> bool:
    if not ident_err:
        return False

    for m in CALL_ARGS_RE.finditer(line):
        fname = m.group("fname")
        if fname in CPP_KEYWORDS:
            continue

        args = m.group("args")
        # literal + ident: printf("%d" n)
        for mm in LIT_IDENT_GLUE_RE.finditer(args):
            if mm.group("right") == ident_err:
                return True
        # operand operand: f(a b) / g(a, b c) / h(a b + c)
        for mm in ADJ_OPERANDS_WS_RE.finditer(args):
            if mm.group("right") == ident_err:
                return True
    return False


COND_RE = re.compile(r"""
                    \b(?:if|while|switch)\s*\((?P<cond>[^()]*)\)
                    """, re.VERBOSE)

def missing_op_in_condition(line : str, ident_err : str | None) -> bool:
    if not ident_err:
        return False

    m = COND_RE.search(line)
    if not m:
        return False

    cond = m.group("cond")
    # literal + ident внутри условия: if ("x" i)  (редко, но бывает)
    for mm in LIT_IDENT_GLUE_RE.finditer(cond):
        if mm.group("right") == ident_err:
            return True
    # operand operand: if (a b), while (x y && z), if (a < b c)
    for mm in ADJ_OPERANDS_WS_RE.finditer(cond):
        left = mm.group("left")
        right = mm.group("right")
        if right != ident_err:
            continue
        # чтобы не спутать с валидным "if (int x = f())" — отсекаем type-keywords слева
        # (это компромисс: иногда будет false negative, но меньше false positive)
        if isinstance(left, str) and left in TYPE_KEYWORDS:
            continue
        return True
    return False


QUALS_RE = r"(?:constexpr|const|volatile|static|extern|register|inline|typename)"
BUILTIN_TYPE_RE = r"""
                (?:signed|unsigned)?\s*
                (?:short|long\s+long|long)?\s*
                (?:int|char|double|float|bool|void)?
                """
USER_TYPE_RE = r"""
                (?:[A-Za-z_]\w*::)*[A-Za-z_]\w*
                (?:\s*<[^;{}()]*>)?
                """
TYPE_RE = rf"(?:{BUILTIN_TYPE_RE}|{USER_TYPE_RE})"
DECL_PREFIX_RE = re.compile(rf"""
                            (?:^|[;{{}}(])\s*
                            (?:{QUALS_RE}\s+)*
                            (?P<type>{TYPE_RE})
                            (?=\s+(?:[\*&]\s*)*[A-Za-z_]\w*)
                            """, re.VERBOSE)
DECL_ADJ_IDENT_RE = re.compile(r"""
                                (?:^|,)\s*
                                (?:[\*&]\s*)*
                                (?P<prev>[A-Za-z_]\w*)
                                [ \t]+
                                (?P<err>[A-Za-z_]\w*)
                                \b
                                (?=\s*(?:=|,|;|\)|\]|\{|\[))
                                """, re.VERBOSE)
BOOL_NULL = r"(?:true|false|nullptr)"
SIMPLE_INIT_RE = rf"(?:{NUM_LIT}|{BOOL_NULL}|{STR}|{CHR})"
DECL_AFTER_INIT_ADJ_IDENT_RE = re.compile(rf"""
                                            \b(?P<prev>[A-Za-z_]\w*)\s*=\s*(?P<init>{SIMPLE_INIT_RE})
                                            [ \t]+
                                            (?P<err>[A-Za-z_]\w*)
                                            \b
                                            (?=\s*(?:=|,|;|\)|\]|\{{|\[))   # '(' нет
                                            """, re.VERBOSE)

CONTROL_START_RE = re.compile(r"^\s*\b(if|for|while|switch|return|case|default|else|do)\b")
STREAM_OP_RE = re.compile(r"<<|>>")

def looks_like_decl(type_part : str) -> bool:
    if not type_part:
        return False
    
    if "::" in type_part or "<" in type_part:
        return True
    toks = IDENT_IN_CODE_RE.findall(type_part)
    return any(t in TYPE_KEYWORDS or t in COMMON_TYPE_ALIASES for t in toks)


def adjacent_idents_need_separator_decl_only(line : str, ident_err : str | None) -> bool:
    """
    Возвращает True только если:
    - строка похожа на объявление переменных/параметров (declaration),
    - и внутри списка декларатора обнаружено "prev err" без запятой
      (где err == ident_err),
    - и эта пара находится ДО '=' в текущем декларатора (чтобы не путать с выражениями).
    """
    if not ident_err or not isinstance(line, str):
        return False
    if CONTROL_START_RE.search(line) or STREAM_OP_RE.search(line):
        return False
    
    m = DECL_PREFIX_RE.search(line)
    if not m:
        return False

    type_part = m.group("type")
    if not looks_like_decl(type_part):
        return False
    
    rest = line[m.end():]
    if ident_err not in rest:
        return False

    for mm in DECL_AFTER_INIT_ADJ_IDENT_RE.finditer(rest):
        if mm.group("err") == ident_err:
                return True
    for mm in DECL_ADJ_IDENT_RE.finditer(rest):
            if mm.group("err") == ident_err:
                return True
    return False