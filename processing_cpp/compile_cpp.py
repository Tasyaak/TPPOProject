import subprocess, uuid, os, re
from config import BUILD_DIR


BUILD_DIR.mkdir(parents=True, exist_ok=True)
CPP_LINE_RE_FIND = re.compile(r"\.cpp\((\d+)\)")
BITS_HEADER_RE_FIND = re.compile(r"(?<= )bits/stdc\+\+\.h(?=:(?!:))")
BITS_HEADER_RE_REPLACE = re.compile(r'#\s*include\s*(<\s*bits/stdc\+\+\.h\s*>|"\s*bits/stdc\+\+\.h\s*")')
CL_CMD_BASE = [
        "cl",
        "/nologo",
        "/c",
        "/EHsc",
        # "/Zs",
        # "/Zi",
        # "/Od",
        # "/MDd",
        "/utf-8",
        "/std:c++14"
        ]

def compile(source_code : str) -> str | None:
    filename = f"tmp_{uuid.uuid4().hex}.cpp"
    cpp_path = BUILD_DIR / filename
    cpp_path.write_text(source_code, encoding="utf-8")
    timeout_sec = 7.5
    
    cmd = CL_CMD_BASE + [str(cpp_path)]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # text=True,
            # encoding="utf-8",
            # errors="replace",
            cwd=str(BUILD_DIR),
            timeout=timeout_sec
        )
    except subprocess.TimeoutExpired:
        return None
    
    raw = proc.stdout
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp866", errors="replace")
    return text


def compile_get_error_info(source_code : str) -> tuple[str | None, int | None]:
    temp = compile(source_code)
    if temp is None:
        return (None, None)
    
    idx = temp.find("error ")
    if idx == -1:
        return (temp.strip(), None)

    m_line = CPP_LINE_RE_FIND.search(temp)
    error_line = int(m_line.group(1)) if m_line else None

    idx += len("error ")
    end_str = temp.find('\n', idx)
    if end_str == -1:
        end_str = len(temp)

    res = temp[idx:end_str].strip()
    # if BITS_HEADER_RE_FIND.search(res):
    #     code = normalize_includes(source_code)
    #     if code == source_code:
    #         return (None, None)
    #     return compile_get_error_info(code)
    return (res, error_line)


def clear_build_tmp() -> None:
    for pattern in ("*.cpp", "*.obj", "*.exe"):
        for file in BUILD_DIR.glob(pattern):
            os.remove(file)


def strip_cpp_comments(code : str) -> str:
    code = code.strip()
    result = []
    i = 0
    n = len(code)
    state = "code"

    while i < n:
        ch = code[i]

        if state == "code":
            # начало строкового литерала
            if ch == '"':
                state = "string"
                result.append(ch)
                i += 1
                continue
            # начало символьного литерала
            if ch == "'":
                state = "char"
                result.append(ch)
                i += 1
                continue
            # потенциальное начало комментария
            if ch == "/" and i + 1 < n:
                next_ch = code[i + 1]
                # // однострочный комментарий
                if next_ch == "/":
                    state = "line_comment"
                    i += 2
                    continue
                # /* ... */ многострочный комментарий
                if next_ch == "*":
                    state = "block_comment"
                    i += 2
                    continue
            # обычный код — просто копируем символ
            result.append(ch)
            i += 1
        elif state == "string":
            result.append(ch)
            # экранированный символ внутри строки
            if ch == "\\" and i + 1 < n:
                result.append(code[i + 1])
                i += 2
                continue
            # конец строкового литерала
            if ch == '"':
                state = "code"
            i += 1
        elif state == "char":
            result.append(ch)
            # экранированный символ внутри символьного литерала
            if ch == "\\" and i + 1 < n:
                result.append(code[i + 1])
                i += 2
                continue
            # конец символьного литерала
            if ch == "'":
                state = "code"
            i += 1
        elif state == "line_comment":
            # пропускаем до конца строки
            if ch == "\n":
                # перевод строки сохраняем, чтобы структура кода не ломалась
                result.append(ch)
                state = "code"
            i += 1
        elif state == "block_comment":
            # ищем закрывающую последовательность */
            if ch == "*" and i + 1 < n and code[i + 1] == "/":
                state = "code"
                i += 2
            else:
                i += 1
    return "".join(result).strip()


def normalize_includes(source_code : str) -> str:
    repl = (
        """
        #include <iostream>
        #include <fstream>
        #include <iomanip>
        #include <sstream>
        #include <streambuf>
        #include <locale>
        #include <codecvt>
        #include <array>
        #include <vector>
        #include <map>
        #include <unordered_map>
        #include <set>
        #include <unordered_set>
        #include <forward_list>
        #include <list>
        #include <queue>
        #include <deque>
        #include <stack>
        #include <bitset>
        #include <algorithm>
        #include <iterator>
        #include <string>
        #include <string_view>
        #include <cmath>
        #include <cstdio>
        #include <cstdlib>
        #include <cstring>
        #include <functional>
        #include <numeric>
        #include <utility>
        #include <limits>
        #include <memory>
        #include <memory_resource>
        #include <scoped_allocator>
        #include <new>
        #include <typeinfo>
        #include <typeindex>
        #include <type_traits>
        #include <optional>
        #include <variant>
        #include <any>
        #include <chrono>
        #include <random>
        #include <ratio>
        #include <valarray>
        #include <complex>
        #include <thread>
        #include <mutex>
        #include <shared_mutex>
        #include <condition_variable>
        #include <future>
        #include <atomic>
        #include <regex>
        #include <exception>
        #include <stdexcept>
        #include <system_error>
        #include <cerrno>
        #include <assert.h>
        """
    )
    if BITS_HEADER_RE_REPLACE.search(source_code):
        source_code = BITS_HEADER_RE_REPLACE.sub(repl, source_code)
    return source_code


def test_cpp() -> None:
    code = """
        #include <bits/stdc++.h>
        using namespace std;

        struct st
        {
            int a1; // C2143
        };

        int main()
        {
            int n;
            cin >> n;
            // MyStruct s;
            map<int, vector<int>> m; // C2146
            for (int i = 0; i < n; i++ // C2146

            // int* mass = new double[n]; // C2440
            int* mass = new int[n];
            for (int i = 0; i < n; i++)
                cin >> mass[i];
        }
    """
    print(compile_get_error_info(code))


if __name__ == "__main__":
    test_cpp()