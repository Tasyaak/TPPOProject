import sqlite3
from sqlite3 import Cursor
from typing import Any
from config import DB_PATH


MAX_CELL_WIDTH = 80

def format_cell(value : Any, max_width : int = MAX_CELL_WIDTH) -> str:
    s = str(value).replace("\n", "\\n")
    if len(s) > max_width:
        return s[:max_width-3] + "..."
    return s


def print_table(cursor : Cursor, table : str) -> None:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]

    cursor.execute(f"SELECT * FROM {table}")
    raw_rows = cursor.fetchall()

    rows = [
        [format_cell(v) for v in row]
        for row in raw_rows
    ]
    widths = [
        max(len(col), *(len(str(row[i])) for row in rows))
        for i, col in enumerate(columns)
    ]

    fmt = " | ".join(f"{{:<{w}}}" for w in widths)

    print(f"\nTABLE: {table}")
    print(fmt.format(*columns))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))
    for row in rows:
        print(fmt.format(*row))


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        print_table(cursor, "error_codes")
        print_table(cursor, "recommendation_templates")
        print_table(cursor, "training_data")


if __name__ == "__main__":
    main()