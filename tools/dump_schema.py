import sqlite3
import sys

db = 'GPTLeague.db'
try:
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name").fetchall()
    for name, type_, sql in rows:
        print(f"{name}|{type_}|{sql}")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
