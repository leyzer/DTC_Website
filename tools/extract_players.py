#!/usr/bin/env python3
"""
Extract unique player names from games CSV and create player mapping CSV.

Usage:
    python tools/extract_players.py --input games.csv --output players.csv
"""

import csv
import argparse
import sys
from pathlib import Path

def extract_unique_players(input_file, output_file):
    """Extract unique player names and create mapping CSV."""

    players = set()

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            # Try to detect delimiter (comma or semicolon)
            sample = f.read(1024)
            f.seek(0)

            delimiter = ';' if ';' in sample else ','
            print(f"Detected delimiter: '{delimiter}'")

            reader = csv.DictReader(f, delimiter=delimiter)

            # Strip whitespace from field names
            if reader.fieldnames:
                reader.fieldnames = [fn.strip() if fn else fn for fn in reader.fieldnames]

            row_count = 0
            for row in reader:
                row_count += 1

                # Strip whitespace from values
                player_one = row.get('player_one', '').strip()
                player_two = row.get('player_two', '').strip()

                if player_one:
                    players.add(player_one)
                if player_two:
                    players.add(player_two)

            print(f"Processed {row_count} games")

    except FileNotFoundError:
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not players:
        print("ERROR: No players found in CSV")
        sys.exit(1)

    # Sort players alphabetically
    players = sorted(players)

    print(f"\nFound {len(players)} unique players:")
    for player in players:
        print(f"  - {player}")

    # Write to output CSV
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['old_name', 'username'])
            writer.writeheader()

            for player in players:
                writer.writerow({
                    'old_name': player,
                    'username': player  # Default: same as old_name, edit as needed
                })

        print(f"\n✓ Created {output_file}")
        print(f"\nNext steps:")
        print(f"1. Edit {output_file} to update usernames if needed")
        print(f"2. Make sure all usernames exist in the database")
        print(f"3. Run the import: python tools/import_games.py --data {input_file} --mapping {output_file} --dry-run")

    except Exception as e:
        print(f"ERROR: Failed to write output file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Extract unique player names from games CSV"
    )
    parser.add_argument(
        "--input",
        default="games.csv",
        help="Input games CSV file (default: games.csv)"
    )
    parser.add_argument(
        "--output",
        default="players.csv",
        help="Output players mapping CSV file (default: players.csv)"
    )

    args = parser.parse_args()
    extract_unique_players(args.input, args.output)


if __name__ == "__main__":
    main()
