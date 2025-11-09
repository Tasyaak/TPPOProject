import sqlite3, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "app.db"
SCHEMA = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
# SEED = (ROOT / "db" / "seed.sql").read_text(encoding="utf-8")

DB_PATH.unlink(missing_ok=True)
with sqlite3.connect(DB_PATH) as conn:
    conn.executescript(SCHEMA)
    # conn.executescript(SEED)

print(f"Created {DB_PATH}")