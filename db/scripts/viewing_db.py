import sqlite3, pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "app.db"


def print_table(conn : sqlite3.Connection, table: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]

    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()

    # Определяем ширину столбцов
    widths = [max(len(str(col)), *(len(str(row[i])) for row in rows)) for i, col in enumerate(columns)]

    # Формируем формат строки
    fmt = " | ".join(f"{{:<{w}}}" for w in widths)

    print(fmt.format(*columns))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))

    for row in rows:
        print(fmt.format(*row))

    conn.close()


def main():
    conn = sqlite3.connect(DB_PATH)
    print_table(conn, "error_codes")
    print_table(conn, "recommendation_templates")
    print_table(conn, "training_data")


if __name__ == "__main__":
    main()