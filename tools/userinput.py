import csv
import sqlite3
import hashlib
from datetime import datetime

# Path to your input file
INPUT_FILE = "games.csv"   # adjust to your actual filename
DB_FILE = "GPTLeague.db"      # your SQLite database file

def hash_password(password: str) -> str:
    """Simple SHA256 hash for demo purposes."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def main():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Create users table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        user_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        is_active INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        full_name TEXT NOT NULL
    );
    """)

    players = set()

    # Read the file
    with open(INPUT_FILE, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=';')  
        for row in reader:
            player_a = row["Player A (person submitting the result) [40k]"].strip()
            player_b = row["Player B (your opponent) [40k]"].strip()
            players.add(player_a)
            players.add(player_b)

    # Insert unique players
    for player in players:
        email = player.replace(" ", ".").lower() + "@example.com"
        user_name = player.split()[0].lower()   # simple username
        password_hash = hash_password("defaultpassword")  # placeholder
        is_active = 1
        created_at = datetime.utcnow().isoformat()
        full_name = player

        try:
            cur.execute("""
                INSERT INTO users (email, user_name, password_hash, is_active, created_at, full_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (email, user_name, password_hash, is_active, created_at, full_name))
        except sqlite3.IntegrityError:
            # Skip if already exists
            print(f"User {player} already exists, skipping.")

    conn.commit()
    conn.close()
    print("Users inserted successfully.")

if __name__ == "__main__":
    main()
