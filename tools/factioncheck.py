import csv
import sqlite3

INPUT_FILE = "games.csv"   # your file
DB_FILE = "GPTLeague.db"   # your SQLite DB

SYSTEM_MAP = {
    "warhammer 40,000": 2,
    "warhammer: age of sigmar": 1
}

def normalize_header(h):
    return h.strip().lower()

def main():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Ensure factions table exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS factions (
        faction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        system_id INTEGER NOT NULL,
        faction_name TEXT NOT NULL,
        UNIQUE(system_id, faction_name),
        FOREIGN KEY(system_id) REFERENCES systems(system_id)
    );
    """)

    factions = set()

    # Read the file
    with open(INPUT_FILE, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=';')
        # normalize headers
        reader.fieldnames = [normalize_header(h) for h in reader.fieldnames]

        for row in reader:
            row = {normalize_header(k): v.strip() for k, v in row.items()}

            system_name = row["what game system did you play?"].lower()
            system_id = SYSTEM_MAP.get(system_name)

            faction_a = row["player a army [40k]"]
            faction_b = row["player b army [40k]"]

            factions.add((system_id, faction_a))
            factions.add((system_id, faction_b))

    # Insert factions
    for system_id, faction_name in factions:
        try:
            cur.execute(
                "INSERT OR IGNORE INTO factions (system_id, faction_name) VALUES (?, ?)",
                (system_id, faction_name)
            )
        except sqlite3.IntegrityError:
            print(f"Faction {faction_name} for system {system_id} already exists, skipping.")

    conn.commit()

    # Confirm factions grouped by system
    cur.execute("SELECT system_id, faction_name FROM factions ORDER BY system_id, faction_name;")
    rows = cur.fetchall()
    print("Factions in database:")
    for system_id, faction_name in rows:
        print(f"System {system_id}: {faction_name}")

    conn.close()

if __name__ == "__main__":
    main()
