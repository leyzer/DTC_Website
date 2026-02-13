import csv
import sqlite3
from datetime import datetime

INPUT_FILE = "cleaned_games.csv"
DB_FILE = "GPTLeague.db"

SYSTEM_MAP = {
    "Warhammer 40,000": 2,
    "Warhammer: Age of Sigmar": 1
}

# Default elo_rule_id mapping for 2000-point games
ELO_RULE_MAP = {
    1: 4,  # AoS
    2: 8   # 40k
}

DATE_FORMATS = [
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y/%m/%d %H:%M:%S",
    "%d-%m-%Y",
]

FACTION_MAP = {
    "Drukari": "Drukhari",
    "Custodes": "Adeptus Custodes",
    "Kharadon Overlords": "Kharadron Overlords",
    "Orgor Mawtribes": "Ogor Mawtribes",
    "Chaos Daemons": "Chaos Daemons",
    "Chaos Space Marines": "Chaos Space Marines",
    "Imperial Knights": "Imperial Knights",
    "Necrons": "Necrons",
    "Aeldari": "Aeldari",
    "Tyranids": "Tyranids",
    "Astra Militarum": "Astra Militarum",
    "Emperor's Children": "Emperor's Children",
    "Stormcast Eternals": "Stormcast Eternals",
    "Soulblight Gravelords": "Soulblight Gravelords",
    "Sons of Behemat": "Sons of Behemat",
    "Orruk Warclans": "Orruk Warclans",
    "Hedonites of Slaanesh": "Hedonites of Slaanesh",
    "Maggotkin of Nurgle": "Maggotkin of Nurgle",
}

USER_MAP = {
    "Brandon W": "Brandon W",
    "Madison L": "Madison L",
    "Kyle J": "Kyle J",
    "Neal C": "Neal C",
    "Maxim B": "Maxim B",
    "Bradley P": "Bradley P",
    "Jashin R": "Jashin R",
    "Andrew B": "Andrew B",
    "Jason V": "Jason V",
    "Robert N": "Robert N",
    "Darryn P": "Darryn P",
}

def normalize_datetime(value):
    if not value or value.strip() == "":
        return ""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return value.strip().replace("/", "-")

def normalize_result(result_str, is_player_a):
    result_str = result_str.lower()
    if "draw" in result_str:
        return "draw"
    if "a won" in result_str:
        return "win" if is_player_a else "loss"
    if "b won" in result_str:
        return "loss" if is_player_a else "win"
    return None

def normalize_flag(value):
    return 1 if value and value.strip().lower() == "yes" else 0

def normalize_faction(name):
    return FACTION_MAP.get(name.strip(), name.strip()) if name else ""

def normalize_user(name):
    return USER_MAP.get(name.strip(), name.strip()) if name else ""

def get_or_create_user(cur, full_name):
    cur.execute("SELECT user_id FROM users WHERE full_name = ?", (full_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    email = full_name.replace(" ", ".").lower() + "@example.com"
    user_name = full_name.split()[0].lower()
    password_hash = "placeholder"
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO users (email, user_name, password_hash, is_active, created_at, full_name)
        VALUES (?, ?, ?, 1, ?, ?)
    """, (email, user_name, password_hash, created_at, full_name))
    return cur.lastrowid

def get_or_create_faction(cur, system_id, faction_name):
    cur.execute("SELECT faction_id FROM factions WHERE system_id = ? AND faction_name = ?", (system_id, faction_name))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO factions (system_id, faction_name) VALUES (?, ?)", (system_id, faction_name))
    return cur.lastrowid

def main():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    with open(INPUT_FILE, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=',')
        # strip spaces from headers
        reader.fieldnames = [fn.strip() for fn in reader.fieldnames]

        for row in reader:
            # strip spaces from keys and values
            row = {k.strip(): (v.strip() if v else "") for k, v in row.items()}

            system_name = row.get("What game system did you play?", "")
            system_id = SYSTEM_MAP.get(system_name)

            played_on = normalize_datetime(row.get("When was the game played?", ""))
            season_id = datetime.strptime(played_on, "%Y-%m-%d %H:%M:%S").year if played_on else None

            result = row.get("What was the result of the game?", "")

            player_a_name = normalize_user(row.get("Player A (person submitting the result)", ""))
            player_b_name = normalize_user(row.get("Player B (your opponent)", ""))
            faction_a_name = normalize_faction(row.get("Player A Army", ""))
            faction_b_name = normalize_faction(row.get("Player B Army", ""))

            painted_a = normalize_flag(row.get("Player A's models [Painted]", ""))
            wysiwyg_a = normalize_flag(row.get("Player A's models [WYSIWYG]", ""))
            battle_ready_a = 1 if painted_a and wysiwyg_a else 0

            painted_b = normalize_flag(row.get("Player B's models [Painted]", ""))
            wysiwyg_b = normalize_flag(row.get("Player B's models [WYSIWYG]", ""))
            battle_ready_b = 1 if painted_b and wysiwyg_b else 0

            points_band = "2000"
            elo_rule_id = ELO_RULE_MAP.get(system_id)

            # Insert game with location_id = 5
            cur.execute("""
                INSERT INTO games (season_id, system_id, played_on, location_id, points_band, notes, score, ignored)
                VALUES (?, ?, ?, 5, ?, NULL, NULL, NULL)
            """, (season_id, system_id, played_on, points_band))
            game_id = cur.lastrowid

            # Ensure elo_rule exists
            cur.execute("""
                INSERT OR IGNORE INTO elo_rules (elo_rule_id, category, points_band, base_rating, k_factor)
                VALUES (?, ?, ?, 1500, 32)
            """, (elo_rule_id, system_name, points_band))

            # Resolve or create users/factions
            player_a_id = get_or_create_user(cur, player_a_name)
            player_b_id = get_or_create_user(cur, player_b_name)
            faction_a_id = get_or_create_faction(cur, system_id, faction_a_name)
            faction_b_id = get_or_create_faction(cur, system_id, faction_b_name)

            # Insert participants
            cur.execute("""
                INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready, score_raw)
                VALUES (?, ?, ?, ?, ?, NULL)
            """, (game_id, player_a_id, faction_a_id, normalize_result(result, True), battle_ready_a))

            cur.execute("""
                INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready, score_raw)
                VALUES (?, ?, ?, ?, ?, NULL)
            """, (game_id, player_b_id, faction_b_id, normalize_result(result, False), battle_ready_b))

            print(f"Imported game {game_id}: {player_a_name} vs {player_b_name} ({system_name}, {points_band} pts, elo_rule {elo_rule_id})")


    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
