#!/usr/bin/env python3
"""
Game Data Importer for DTC League
Imports game results from CSV with player name mapping.

Required CSV columns: system_id, date, player_one, score_one, player_two, score_two
Player mapping CSV columns: old_name, username

Usage:
    python import_games.py --data games.csv --mapping players.csv [--dry-run]
"""

import csv
import sqlite3
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Database file
DB_FILE = "GPTLeague.db"

# ELO rule ID mapping for 2000-point games
ELO_RULE_MAP = {
    1: 4,   # AoS (Age of Sigmar)
    2: 8    # 40k (Warhammer 40,000)
}

# System names for elo_rules
SYSTEM_NAMES = {
    1: "Age of Sigmar",
    2: "Warhammer 40,000"
}

DATE_FORMATS = [
    "%d-%b-%Y",        # 31-Dec-2024
    "%m/%d/%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
]


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Import game results from CSV with player mapping"
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to CSV file with game data (system_id, date, player_one, score_one, player_two, score_two)"
    )
    parser.add_argument(
        "--mapping",
        required=True,
        help="Path to CSV file with player name mapping (old_name, username)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving to database"
    )
    return parser.parse_args()


def load_player_mapping(mapping_file):
    """Load player name to username mapping from CSV."""
    mapping = {}
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            # Auto-detect delimiter
            sample = f.read(1024)
            f.seek(0)
            delimiter = ';' if ';' in sample else ','

            reader = csv.DictReader(f, delimiter=delimiter, fieldnames=['old_name', 'username'])
            next(reader)  # Skip header if it exists
            for row in reader:
                if row['old_name'] and row['username']:
                    mapping[row['old_name'].strip()] = row['username'].strip()
    except Exception as e:
        print(f"ERROR: Failed to load player mapping: {e}")
        sys.exit(1)
    return mapping


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


def determine_result(score_one, score_two, is_player_one):
    """Determine game result from scores."""
    try:
        p1_score = int(score_one)
        p2_score = int(score_two)
    except (ValueError, TypeError):
        return None

    if p1_score > p2_score:
        return "win" if is_player_one else "loss"
    elif p1_score < p2_score:
        return "loss" if is_player_one else "win"
    else:
        return "draw"


def get_or_create_location(cursor, location_name="Imported Games"):
    """Get or create a location."""
    cursor.execute(
        "SELECT location_id FROM locations WHERE name = ?",
        (location_name,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO locations (name, location_type) VALUES (?, 'other')",
        (location_name,)
    )
    return cursor.lastrowid


def get_or_create_faction(cursor, system_id, faction_name):
    """Get or create a faction for a system."""
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


def get_user_by_username(cursor, username):
    """Get user ID by username."""
    cursor.execute(
        "SELECT user_id FROM users WHERE user_name = ?",
        (username,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def insert_game(cursor, game_data, dry_run=False):
    """Insert a single game and return success status."""
    try:
        season_id = game_data['season_id']
        system_id = game_data['system_id']
        played_on = game_data['played_on']
        location_id = game_data['location_id']
        player_one_id = game_data['player_one_id']
        player_two_id = game_data['player_two_id']
        faction_one_id = game_data['faction_one_id']
        faction_two_id = game_data['faction_two_id']
        result_one = game_data['result_one']
        result_two = game_data['result_two']

        if dry_run:
            print(f"  [DRY-RUN] Would insert game:")
            print(f"    System: {SYSTEM_NAMES.get(system_id, system_id)}")
            print(f"    Date: {played_on}")
            print(f"    Player 1: {game_data['player_one_name']} (ID: {player_one_id}, Faction: {game_data['faction_one_name']})")
            print(f"    Player 2: {game_data['player_two_name']} (ID: {player_two_id}, Faction: {game_data['faction_two_name']})")
            print(f"    Result: {result_one} vs {result_two}")
            return True

        cursor.execute("BEGIN")

        # Insert game
        cursor.execute(
            """INSERT INTO games (season_id, system_id, played_on, location_id, points_band, notes, score, ignored)
               VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)""",
            (season_id, system_id, played_on, location_id, "2000", "Imported from CSV")
        )
        game_id = cursor.lastrowid

        # Ensure elo_rule exists
        elo_rule_id = ELO_RULE_MAP.get(system_id)
        system_name = SYSTEM_NAMES.get(system_id)
        cursor.execute(
            """INSERT OR IGNORE INTO elo_rules (elo_rule_id, category, points_band, base_rating, k_factor)
               VALUES (?, ?, ?, 1500, 32)""",
            (elo_rule_id, system_name, "2000")
        )

        # Insert player 1
        cursor.execute(
            """INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready, score_raw)
               VALUES (?, ?, ?, ?, 0, NULL)""",
            (game_id, player_one_id, faction_one_id, result_one)
        )

        # Insert player 2
        cursor.execute(
            """INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready, score_raw)
               VALUES (?, ?, ?, ?, 0, NULL)""",
            (game_id, player_two_id, faction_two_id, result_two)
        )

        cursor.execute("COMMIT")

        print(f"  ✓ Imported game {game_id}: {game_data['player_one_name']} vs {game_data['player_two_name']}")
        return True

    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"  ✗ Error inserting game: {e}")
        return False


def validate_system_id(system_id):
    """Validate system ID."""
    if system_id not in [1, 2]:
        print(f"  ERROR: Invalid system_id '{system_id}'. Must be 1 (AoS) or 2 (40k)")
        return False
    return True


def main():
    args = parse_arguments()

    # Load player mapping
    print("Loading player mapping...")
    player_mapping = load_player_mapping(args.mapping)
    print(f"  Loaded {len(player_mapping)} player mappings")

    # Open database
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
    except Exception as e:
        print(f"ERROR: Failed to open database: {e}")
        sys.exit(1)

    # Pre-fetch location (or create if needed)
    location_id = get_or_create_location(cursor, "Imported Games")

    # Process games CSV
    print(f"\nProcessing {args.data}...")

    created_factions = {}  # Track new factions created
    total_rows = 0
    successful_imports = 0
    failed_imports = 0
    skipped_rows = 0

    try:
        with open(args.data, 'r', encoding='utf-8') as f:
            # Auto-detect delimiter (comma or semicolon)
            sample = f.read(1024)
            f.seek(0)
            delimiter = ';' if ';' in sample else ','
            print(f"Detected CSV delimiter: '{delimiter}'")

            reader = csv.DictReader(f, delimiter=delimiter)

            # Strip whitespace from field names
            if reader.fieldnames:
                reader.fieldnames = [fn.strip() if fn else fn for fn in reader.fieldnames]

            for row_num, row in enumerate(reader, start=2):  # Start at 2 since row 1 is header
                total_rows += 1

                # Strip whitespace from values
                row = {k: (v.strip() if v else v) for k, v in row.items() if k}

                print(f"\nRow {row_num}:")

                # Parse system ID
                try:
                    system_id = int(row.get('system_id', ''))
                except (ValueError, TypeError):
                    print(f"  SKIP: Invalid system_id '{row.get('system_id', '')}'")
                    skipped_rows += 1
                    continue

                if not validate_system_id(system_id):
                    skipped_rows += 1
                    continue

                # Parse date
                date_str = row.get('date', '')
                played_on = parse_date(date_str)
                if not played_on:
                    print(f"  SKIP: Could not parse date '{date_str}'")
                    skipped_rows += 1
                    continue

                season_id = int(played_on[:4])  # Extract year

                # Get player names and map them
                player_one_name_raw = row.get('player_one', '').strip()
                player_two_name_raw = row.get('player_two', '').strip()

                if not player_one_name_raw or not player_two_name_raw:
                    print(f"  SKIP: Missing player names")
                    skipped_rows += 1
                    continue

                # Look up in mapping
                player_one_username = player_mapping.get(player_one_name_raw)
                player_two_username = player_mapping.get(player_two_name_raw)

                if not player_one_username:
                    print(f"  WARN: No mapping for player '{player_one_name_raw}', skipping row")
                    skipped_rows += 1
                    continue

                if not player_two_username:
                    print(f"  WARN: No mapping for player '{player_two_name_raw}', skipping row")
                    skipped_rows += 1
                    continue

                # Get user IDs
                player_one_id = get_user_by_username(cursor, player_one_username)
                player_two_id = get_user_by_username(cursor, player_two_username)

                if not player_one_id:
                    print(f"  ERROR: User '{player_one_username}' not found in database")
                    skipped_rows += 1
                    continue

                if not player_two_id:
                    print(f"  ERROR: User '{player_two_username}' not found in database")
                    skipped_rows += 1
                    continue

                # Parse scores and determine results
                try:
                    score_one = int(row.get('score_one', 0))
                    score_two = int(row.get('score_two', 0))
                except (ValueError, TypeError):
                    print(f"  ERROR: Invalid scores")
                    skipped_rows += 1
                    continue

                result_one = determine_result(score_one, score_two, True)
                result_two = determine_result(score_one, score_two, False)

                if not result_one or not result_two:
                    print(f"  ERROR: Could not determine result from scores")
                    skipped_rows += 1
                    continue

                # Get or create factions (both default to TBD for this system)
                faction_name = f"TBD ({SYSTEM_NAMES.get(system_id, system_id)})"
                faction_one_id = get_or_create_faction(cursor, system_id, faction_name)
                faction_two_id = get_or_create_faction(cursor, system_id, faction_name)

                # Track if we created a new faction
                if faction_name not in created_factions:
                    created_factions[faction_name] = faction_one_id

                # Prepare game data
                game_data = {
                    'season_id': season_id,
                    'system_id': system_id,
                    'played_on': played_on,
                    'location_id': location_id,
                    'player_one_id': player_one_id,
                    'player_one_name': player_one_username,
                    'player_two_id': player_two_id,
                    'player_two_name': player_two_username,
                    'faction_one_id': faction_one_id,
                    'faction_one_name': faction_name,
                    'faction_two_id': faction_two_id,
                    'faction_two_name': faction_name,
                    'result_one': result_one,
                    'result_two': result_two,
                }

                # Insert game
                if insert_game(cursor, game_data, dry_run=args.dry_run):
                    successful_imports += 1
                else:
                    failed_imports += 1

        # Summary report
        print("\n" + "=" * 60)
        print("IMPORT SUMMARY")
        print("=" * 60)
        print(f"Total rows processed: {total_rows}")
        print(f"Successfully imported: {successful_imports}")
        print(f"Failed imports: {failed_imports}")
        print(f"Skipped rows: {skipped_rows}")

        if created_factions:
            print(f"\nNew factions created: {len(created_factions)}")
            for faction_name in created_factions:
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
