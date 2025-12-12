import sqlite3
from config import DB_PATH, SCHEMA_SQL_PATH, SEED_SQL_PATH


DB_PATH.unlink(missing_ok=True)
with sqlite3.connect(DB_PATH) as conn:
    with open(SCHEMA_SQL_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    with open(SEED_SQL_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())

print(f"Database created {DB_PATH}")