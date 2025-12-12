import random, sqlite3, re, yaml, hashlib
from sqlite3 import Connection
from processing_cpp import compile_get_error_info
from config import DB_PATH, TEMPLATES_YAML_PATH


def has_target_error(error_text : str | None, error_code : str) -> bool:
    if error_text is None:
        return False
    
    pattern = rf"\b{re.escape(error_code)}\b"
    return re.search(pattern, error_text) is not None


def generate_source_from_pattern(pattern : str, placeholders : dict[str, list[str]]) -> str:
    code = pattern
    for name, values in placeholders.items():
        token = f"<{name}>"
        if token in code:
            value = random.choice(values)
            code = code.replace(token, value)
    return code


def find_entry_yaml(config : list[dict], template : str) -> dict:
    for item in config:
        if item.get("template") == template:
            return item
    return {}


def insert_sample(conn : Connection, label_id : int, source_code : str, error_text : str) -> bool:
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO training_data (label, source_code, error_text) VALUES (?, ?, ?)",
            (label_id, source_code, error_text))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    

def code_hash(s : str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def fill_db(template : str, target_count : int = 200) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    config = yaml.safe_load(TEMPLATES_YAML_PATH.read_text(encoding="utf-8"))
    entry = find_entry_yaml(config, template)
    patterns = entry["patterns"]

    cur.execute(
        """
        SELECT recommendation_template_id
        FROM recommendation_templates
        WHERE template = ?
        """, (template,))
    recommendation_template_id, = cur.fetchone()

    cur.execute(
        """
        SELECT error_code
        FROM error_codes
        WHERE error_code_id = (SELECT error_code_id 
                                FROM recommendation_templates
                                WHERE recommendation_template_id = ?)
        """, (recommendation_template_id,))
    error_code, = cur.fetchone()

    cur.execute(
        "SELECT COUNT(*) FROM training_data WHERE label = ?", (recommendation_template_id,))
    count, = cur.fetchone()

    seen_hashes = []
    while count < target_count:
        pattern = random.choice(patterns)
        source_template = pattern["source"]
        placeholders = pattern.get("placeholders", {})
        source_code = generate_source_from_pattern(source_template, placeholders)

        h = code_hash(source_code)
        if h in seen_hashes:
            continue
        seen_hashes.append(h)

        error_text, error_line = compile_get_error_info(source_code)

        if has_target_error(error_text, error_code):
            if insert_sample(conn, recommendation_template_id, source_code, error_text):    # type: ignore
                count += 1
                print(f"added sample {count}/{target_count}")
            else:
                print("duplicate source, regenerating")
        else:
            print(f"skip: no {error_code} in output, error: {error_text}")
    conn.close()


def main() -> None:
    print("template = ", end="")
    template = input()
    print("target_count = ", end="")
    target_count = int(input())
    fill_db(template, target_count)


if __name__ == "__main__":
    main()