#!/usr/bin/env python3
"""
Unified Game Data Importer for DTC League
Accepts both Format 1 (simple CSV) and Format 2 (Google Form) automatically.
Auto-creates missing users with temporary passwords.

Format 1 columns: system_id, date, player_one, score_one, player_two, score_two
Format 2 columns: Timestamp, What game system did you play?, When was the game played?,
                  What was the result of the game?, Player A (person submitting the result),
                  Player A's models [Painted], Player A's models [WYSIWYG], Player A Army,
                  Player B (your opponent), Player B's models [Painted], Player B's models [WYSIWYG], Player B Army

Usage:
    python auto_import.py --data games.csv [--dry-run]
"""

import csv
import sqlite3
import argparse
import sys
import bcrypt
from datetime import datetime
from pathlib import Path

DB_FILE = "GPTLeague.db"

SYSTEM_MAP = {
    "Warhammer 40,000": 2,
    "Warhammer: Age of Sigmar": 1,
}

ELO_RULE_MAP = {
    1: 4,   # AoS
    2: 8    # 40k
}

SYSTEM_NAMES = {
    1: "Age of Sigmar",
    2: "Warhammer 40,000"
}

DATE_FORMATS = [
    "%d-%b-%Y",
    "%m/%d/%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
]


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Unified import for both Format 1 and Format 2 game data"
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to CSV file (Format 1 or Format 2 auto-detected)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving to database"
    )
    return parser.parse_args()


def detect_delimiter(file_path):
    """Detect CSV delimiter (comma or semicolon)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        sample = f.read(1024)
    return ';' if ';' in sample else ','


def detect_format(fieldnames):
    """Detect if this is Format 1 or Format 2."""
    fieldnames_lower = [fn.lower() if fn else fn for fn in fieldnames]

    # Format 1 indicators
    if 'system_id' in fieldnames_lower and 'score_one' in fieldnames_lower:
        return 1

    # Format 2 indicators
    if any('game system' in fn.lower() for fn in fieldnames_lower):
        return 2

    return None


def parse_date(date_str):
    """Parse date string in multiple formats."""
    if not date_str or date_str.strip() == "":
        return None

    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    print(f"  WARNING: Could not parse date '{date_str}'")
    return None


def get_utc_now():
    """Get current UTC time."""
    try:
        from datetime import UTC
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    except ImportError:
        # Fallback for older Python versions
        import time
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password):
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_user_if_missing(cursor, username, full_name, created_users):
    """Create user if they don't exist."""
    cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (username,))
    row = cursor.fetchone()

    if row:
        return row[0]  # User exists

    # Create new user
    email = username.lower().replace(" ", ".") + "@imported.local"
    temp_password = "TempPassword123!"
    password_hash = hash_password(temp_password)
    created_at = get_utc_now()

    cursor.execute(
        """INSERT INTO users (email, user_name, password_hash, is_active, created_at, full_name)
           VALUES (?, ?, ?, 1, ?, ?)""",
        (email, username, password_hash, created_at, full_name)
    )
    user_id = cursor.lastrowid

    # Track for later reporting
    created_users.append({
        'username': username,
        'full_name': full_name,
        'temp_password': temp_password
    })

    return user_id


def get_or_create_faction(cursor, system_id, faction_name):
    """Get or create a faction."""
    cursor.execute(
        "SELECT faction_id FROM factions WHERE system_id = ? AND faction_name = ?",
        (system_id, faction_name)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO factions (system_id, faction_name) VALUES (?, ?)",
        (system_id, faction_name)
    )
    return cursor.lastrowid


def get_or_create_location(cursor):
    """Get or create 'Imported Games' location."""
    cursor.execute("SELECT location_id FROM locations WHERE name = ?", ("Imported Games",))
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO locations (name, location_type) VALUES (?, 'other')",
        ("Imported Games",)
    )
    return cursor.lastrowid


def ensure_system_membership_active(cursor, player_id, system_id):
    """Ensure a player has an active membership in a system."""
    try:
        # Try to update existing membership to active
        cursor.execute(
            "UPDATE system_memberships SET is_active = 1 WHERE player_id = ? AND system_id = ?",
            (player_id, system_id)
        )

        # If no row was updated, create new membership
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO system_memberships (player_id, system_id, is_active) VALUES (?, ?, 1)",
                (player_id, system_id)
            )
    except Exception as e:
        # If membership creation/update fails, log it but don't fail the game import
        print(f"    [Note] Could not set system membership: {e}")


def parse_result_format2(result_str, is_player_a):
    """Parse result from Format 2 (Google Form) result field."""
    result_str = result_str.lower()

    if 'draw' in result_str:
        return "draw"
    if 'player a won' in result_str or 'player a wins' in result_str:
        return "win" if is_player_a else "loss"
    if 'player b won' in result_str or 'player b wins' in result_str:
        return "loss" if is_player_a else "win"

    return None


def parse_battle_ready_format2(painted_a, wysiwyg_a):
    """Determine battle ready status from Format 2 checkboxes."""
    return 1 if (painted_a and painted_a.lower() == 'yes') and (wysiwyg_a and wysiwyg_a.lower() == 'yes') else 0


def insert_game(cursor, game_data, dry_run=False):
    """Insert a single game."""
    try:
        if dry_run:
            print(f"  [DRY-RUN] Game: {game_data['p1_name']} vs {game_data['p2_name']}")
            print(f"    System: {SYSTEM_NAMES.get(game_data['system_id'])}")
            print(f"    Date: {game_data['played_on']}")
            print(f"    Result: {game_data['result_one']} vs {game_data['result_two']}")
            return True

        # Insert game
        cursor.execute(
            """INSERT INTO games (season_id, system_id, played_on, location_id, points_band, notes, score, ignored)
               VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)""",
            (game_data['season_id'], game_data['system_id'], game_data['played_on'],
             game_data['location_id'], "2000", "Imported from CSV")
        )
        game_id = cursor.lastrowid

        # Ensure elo_rule exists
        elo_rule_id = ELO_RULE_MAP.get(game_data['system_id'])
        system_name = SYSTEM_NAMES.get(game_data['system_id'])
        cursor.execute(
            """INSERT OR IGNORE INTO elo_rules (elo_rule_id, category, points_band, base_rating, k_factor)
               VALUES (?, ?, ?, 1500, 32)""",
            (elo_rule_id, system_name, "2000")
        )

        # Insert player 1
        cursor.execute(
            """INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready, score_raw)
               VALUES (?, ?, ?, ?, ?, NULL)""",
            (game_id, game_data['p1_id'], game_data['f1_id'], game_data['result_one'], game_data['p1_battle_ready'])
        )

        # Insert player 2
        cursor.execute(
            """INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready, score_raw)
               VALUES (?, ?, ?, ?, ?, NULL)""",
            (game_id, game_data['p2_id'], game_data['f2_id'], game_data['result_two'], game_data['p2_battle_ready'])
        )

        # Ensure both players are active members of this system
        ensure_system_membership_active(cursor, game_data['p1_id'], game_data['system_id'])
        ensure_system_membership_active(cursor, game_data['p2_id'], game_data['system_id'])

        print(f"  ✓ Imported: {game_data['p1_name']} vs {game_data['p2_name']}")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def process_format1(cursor, reader, created_users, dry_run=False):
    """Process Format 1 CSV data."""
    imported = 0
    failed = 0
    skipped = 0

    location_id = get_or_create_location(cursor)

    for row_num, row in enumerate(reader, start=2):
        row = {k: (v.strip() if v else v) for k, v in row.items() if k}

        print(f"Row {row_num}:")

        try:
            system_id = int(row.get('system_id', ''))
        except (ValueError, TypeError):
            print(f"  SKIP: Invalid system_id")
            skipped += 1
            continue

        date_str = row.get('date', '').strip()
        played_on = parse_date(date_str)
        if not played_on:
            print(f"  SKIP: Could not parse date")
            skipped += 1
            continue

        season_id = int(played_on[:4])

        p1_name = row.get('player_one', '').strip()
        p2_name = row.get('player_two', '').strip()

        if not p1_name or not p2_name:
            print(f"  SKIP: Missing player names")
            skipped += 1
            continue

        try:
            score_one = int(row.get('score_one', 0))
            score_two = int(row.get('score_two', 0))
        except (ValueError, TypeError):
            print(f"  SKIP: Invalid scores")
            skipped += 1
            continue

        # Determine result
        if score_one > score_two:
            result_one, result_two = 'win', 'loss'
        elif score_one < score_two:
            result_one, result_two = 'loss', 'win'
        else:
            result_one, result_two = 'draw', 'draw'

        # Get or create users
        p1_id = create_user_if_missing(cursor, p1_name, p1_name, created_users)
        p2_id = create_user_if_missing(cursor, p2_name, p2_name, created_users)

        # Create TBD factions for Format 1
        faction_name = f"TBD ({SYSTEM_NAMES.get(system_id, system_id)})"
        f1_id = get_or_create_faction(cursor, system_id, faction_name)
        f2_id = get_or_create_faction(cursor, system_id, faction_name)

        game_data = {
            'season_id': season_id,
            'system_id': system_id,
            'played_on': played_on,
            'location_id': location_id,
            'p1_id': p1_id,
            'p1_name': p1_name,
            'p1_battle_ready': 0,
            'p2_id': p2_id,
            'p2_name': p2_name,
            'p2_battle_ready': 0,
            'f1_id': f1_id,
            'f2_id': f2_id,
            'result_one': result_one,
            'result_two': result_two,
        }

        if insert_game(cursor, game_data, dry_run):
            imported += 1
        else:
            failed += 1

    return imported, failed, skipped


def process_format2(cursor, reader, created_users, dry_run=False):
    """Process Format 2 (Google Form) CSV data."""
    imported = 0
    failed = 0
    skipped = 0
    created_factions = {}

    location_id = get_or_create_location(cursor)

    for row_num, row in enumerate(reader, start=2):
        row = {k: (v.strip() if v else v) for k, v in row.items() if k}

        print(f"Row {row_num}:")

        # Extract and validate system
        system_name = row.get('What game system did you play?', '').strip()
        system_id = SYSTEM_MAP.get(system_name)
        if not system_id:
            print(f"  SKIP: Unknown system '{system_name}'")
            skipped += 1
            continue

        # Parse date
        date_str = row.get('When was the game played?', '').strip()
        played_on = parse_date(date_str)
        if not played_on:
            print(f"  SKIP: Could not parse date")
            skipped += 1
            continue

        season_id = int(played_on[:4])

        # Get player names
        p1_name = row.get('Player A (person submitting the result)', '').strip()
        p2_name = row.get('Player B (your opponent)', '').strip()

        if not p1_name or not p2_name:
            print(f"  SKIP: Missing player names")
            skipped += 1
            continue

        # Parse result
        result_str = row.get('What was the result of the game?', '').strip()
        result_one = parse_result_format2(result_str, True)
        result_two = parse_result_format2(result_str, False)

        if not result_one or not result_two:
            print(f"  SKIP: Could not parse result")
            skipped += 1
            continue

        # Parse battle ready
        p1_painted = row.get("Player A's models [Painted]", '').strip()
        p1_wysiwyg = row.get("Player A's models [WYSIWYG]", '').strip()
        p1_battle_ready = parse_battle_ready_format2(p1_painted, p1_wysiwyg)

        p2_painted = row.get("Player B's models [Painted]", '').strip()
        p2_wysiwyg = row.get("Player B's models [WYSIWYG]", '').strip()
        p2_battle_ready = parse_battle_ready_format2(p2_painted, p2_wysiwyg)

        # Get factions
        f1_name = row.get('Player A Army', '').strip()
        f2_name = row.get('Player B Army', '').strip()

        if not f1_name or not f2_name:
            print(f"  SKIP: Missing faction names")
            skipped += 1
            continue

        # Get or create users
        p1_id = create_user_if_missing(cursor, p1_name, p1_name, created_users)
        p2_id = create_user_if_missing(cursor, p2_name, p2_name, created_users)

        # Get or create factions with real names
        f1_id = get_or_create_faction(cursor, system_id, f1_name)
        f2_id = get_or_create_faction(cursor, system_id, f2_name)

        if f1_name not in created_factions:
            created_factions[f1_name] = f1_id
        if f2_name not in created_factions:
            created_factions[f2_name] = f2_id

        game_data = {
            'season_id': season_id,
            'system_id': system_id,
            'played_on': played_on,
            'location_id': location_id,
            'p1_id': p1_id,
            'p1_name': p1_name,
            'p1_battle_ready': p1_battle_ready,
            'p2_id': p2_id,
            'p2_name': p2_name,
            'p2_battle_ready': p2_battle_ready,
            'f1_id': f1_id,
            'f2_id': f2_id,
            'result_one': result_one,
            'result_two': result_two,
        }

        if insert_game(cursor, game_data, dry_run):
            imported += 1
        else:
            failed += 1

    return imported, failed, skipped, created_factions


def main():
    args = parse_arguments()

    # Detect delimiter
    delimiter = detect_delimiter(args.data)
    print(f"Detected delimiter: '{delimiter}'")

    # Read and detect format
    with open(args.data, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = reader.fieldnames
        if fieldnames:
            fieldnames = [fn.strip() if fn else fn for fn in fieldnames]

    data_format = detect_format(fieldnames)

    if not data_format:
        print("ERROR: Could not determine CSV format (expected Format 1 or Format 2)")
        sys.exit(1)

    print(f"Detected format: Format {data_format}")

    # Open database
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
    except Exception as e:
        print(f"ERROR: Failed to open database: {e}")
        sys.exit(1)

    created_users = []
    created_factions = {}

    # Process data
    print(f"\nProcessing {args.data}...\n")

    try:
        with open(args.data, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if reader.fieldnames:
                reader.fieldnames = [fn.strip() if fn else fn for fn in reader.fieldnames]

            if data_format == 1:
                imported, failed, skipped = process_format1(cursor, reader, created_users, args.dry_run)
                created_factions_count = 0
            else:
                imported, failed, skipped, created_factions = process_format2(cursor, reader, created_users, args.dry_run)
                created_factions_count = len(created_factions)

        # Summary
        print("\n" + "="*70)
        print("IMPORT SUMMARY")
        print("="*70)
        print(f"Format: {data_format}")
        print(f"Successfully imported: {imported}")
        print(f"Failed imports: {failed}")
        print(f"Skipped rows: {skipped}")

        if created_users:
            print(f"\nNew users created: {len(created_users)}")
            print("WARNING: Set passwords for these users!")
            for user in created_users:
                print(f"  - {user['username']} (temp: {user['temp_password']})")

        if created_factions_count > 0:
            print(f"\nNew factions created: {created_factions_count}")
            for faction_name in sorted(created_factions.keys()):
                print(f"  - {faction_name}")

        if args.dry_run:
            print("\n[DRY-RUN MODE] No changes saved to database")
        else:
            conn.commit()
            print("\nChanges committed to database")

    except FileNotFoundError:
        print(f"ERROR: File not found: {args.data}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
