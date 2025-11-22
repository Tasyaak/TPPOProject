import random, subprocess, sqlite3, re, yaml
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "app.db"
YAML_PATH = BASE_DIR / "templates.yaml"
BUILD_DIR = BASE_DIR / "build_tmp"   # временная папка для tmp.cpp и .obj/.pch


def compile_and_get_errors(source_code : str) -> str:
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
    res = proc.stdout.strip()
    print(f"res1 = {res}")
    end_str = res.find('\n', 9) 
    if end_str != -1:
        res = res[res.find("error ")+6 : end_str]
    else:
        res = res[res.find("error ")+6 :]
    print(f"res2 = {res}", end="\n\n")
    return res


def has_target_error(error_text : str, error_code : str) -> bool:
    pattern = rf"\b{re.escape(error_code)}\b"
    return re.search(pattern, error_text) is not None


def generate_source_from_pattern(pattern : str, placeholders : dict[str, list[int]]) -> str:
    code = pattern
    for name, values in placeholders.items():
        token = f"<{name}>"
        if token in code:
            value = random.choice(values)
            code = code.replace(token, value)
    return code


def find_entry_yaml(config, template_id: int | str):
    template_id = str(template_id)
    for item in config:
        if str(item.get("recommendation_template_id")) == template_id:
            return item
    return None


def fill_db(recommendation_template_id : int, target_per_template : int = 200) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    config = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    entry = find_entry_yaml(config, recommendation_template_id)
    patterns = entry["patterns"]

    cur.execute(
        """
        SELECT error_code_id, error_code
        FROM error_codes
        WHERE error_code_id = (SELECT error_code_id 
                                FROM recommendation_templates r
                                WHERE recommendation_template_id = ?)
        """, (recommendation_template_id,))
    label_id, error_code = cur.fetchone()

    cur.execute(
        "SELECT COUNT(*) FROM training_data WHERE label = ?", (recommendation_template_id,))
    count, = cur.fetchone()

    while count < target_per_template:
        pattern = random.choice(patterns)
        source_template = pattern["source"]
        placeholders = pattern.get("placeholders", {})
        source_code = generate_source_from_pattern(source_template, placeholders)
        error_text = compile_and_get_errors(source_code)

        if has_target_error(error_text, error_code):
            cur.execute(
                "INSERT INTO training_data (label, source_code, error_text) VALUES (?, ?, ?)",
                (label_id, source_code, error_text)
            )
            conn.commit()
            count += 1
            print(f"added sample {count}/{target_per_template}")
        else:
            print(f"skip: no {error_code} in output")
    conn.close()


def main():
    print("recommendation_template_id, count = ", end="")
    recommendation_template_id, count = map(int, input().split())
    fill_db(recommendation_template_id, count)


if __name__ == "__main__":
    main()