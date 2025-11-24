import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
BUILD_DIR = BASE_DIR / "build_tmp"   # временная папка для tmp.cpp и .obj/.pch


def compile(source_code : str) -> str:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    cpp_path = BUILD_DIR / "tmp.cpp"
    cpp_path.write_text(source_code, encoding="utf-8")

    cmd = [
        "cl",
        "/nologo",
        "/c",
        "/EHsc",
        "/Zi",
        "/Od",
        "/MDd",
        "/std:c++14",
        str(cpp_path)
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        cwd=str(BUILD_DIR)
    )
    return proc.stdout


def compile_get_error_text(source_code : str) -> str:
    res = compile(source_code)
    end_str = res.find('\n', 9) 
    if end_str != -1:
        res = res[res.find("error ")+6 : end_str]
    else:
        res = res[res.find("error ")+6 :]
    return res


def test_cpp():
    code = """
        #include <iostream>
        #include <vector>
        #include <map>
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
            map<int, vector<int> m; // C2146
            // for (int i = 0; i < n; i++ // C2146

            // int* mass = new double[n]; // C2440
            int* mass = new int[n];
            for (int i = 0; i < n; i++)
                cin >> mass[i];
        }
    """
    print(compile(code))


if __name__ == "__main__":
    test_cpp()