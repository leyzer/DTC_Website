import csv
import argparse
from datetime import datetime
from collections import Counter

FACTION_MAP = {
    "Drukari": "Drukhari",
    "Drukari ": "Drukhari",
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

DATE_FORMATS = [
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y/%m/%d %H:%M:%S",
    "%d-%m-%Y",
]

# ---------------- Normalization Helpers ----------------
def normalize_datetime(value):
    if not value or value.strip() == "":
        return ""
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(value.strip(), fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return value.strip().replace("/", "-")

def normalize_result(value):
    if not value:
        return ""
    v = value.strip().lower()
    if "player a won" in v:
        return "A_win"
    elif "player b won" in v:
        return "B_win"
    elif "draw" in v:
        return "draw"
    return v

def normalize_flag(value):
    return 1 if value and value.strip().lower() == "yes" else 0

def normalize_faction(name):
    return FACTION_MAP.get(name.strip(), name.strip()) if name else ""

def normalize_user(name):
    return USER_MAP.get(name.strip(), name.strip()) if name else ""

def normalize_wysiwyg(value):
    return 1 if value and value.strip().lower() == "yes" else 0

# ---------------- Pipeline Functions ----------------
def read_csv(input_file):
    with open(input_file, newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile, delimiter=";")
        # strip spaces from headers
        reader.fieldnames = [fn.strip() for fn in reader.fieldnames]
        rows = []
        for row in reader:
            # strip spaces from keys and values
            cleaned_row = {k.strip(): (v.strip() if v else "") for k, v in row.items()}
            rows.append(cleaned_row)
        return reader.fieldnames, rows

def clean_rows(rows):
    system_counter = Counter()
    player_counter = Counter()
    faction_counter = Counter()

    cleaned = []
    for row in rows:
        # Normalize date
        played_on = row.get("When was the game played?")
        normalized_date = normalize_datetime(played_on)
        row["normalized_played_on"] = normalized_date
        row["season_year"] = datetime.strptime(normalized_date, "%Y-%m-%d %H:%M:%S").year if normalized_date else ""

        # Normalize result
        row["normalized_result"] = normalize_result(row.get("What was the result of the game?"))

        # Player A
        painted_a = normalize_flag(row.get("Player A's models [Painted]"))
        wysiwyg_a = normalize_wysiwyg(row.get("Player A's models [WYSIWYG]"))
        row["playerA_battle_ready"] = 1 if (painted_a and wysiwyg_a) else 0

        # Player B
        painted_b = normalize_flag(row.get("Player B's models [Painted]"))
        wysiwyg_b = normalize_wysiwyg(row.get("Player B's models [WYSIWYG]"))
        row["playerB_battle_ready"] = 1 if (painted_b and wysiwyg_b) else 0

        # Normalize users and factions
        row["playerA_user_clean"] = normalize_user(row.get("Player A (person submitting the result)"))
        row["playerB_user_clean"] = normalize_user(row.get("Player B (your opponent)"))
        row["playerA_faction_clean"] = normalize_faction(row.get("Player A Army"))
        row["playerB_faction_clean"] = normalize_faction(row.get("Player B Army"))

        # Count stats
        system = row.get("What game system did you play?", "")
        if system:
            system_counter[system] += 1
        if row["playerA_user_clean"]:
            player_counter[row["playerA_user_clean"]] += 1
        if row["playerB_user_clean"]:
            player_counter[row["playerB_user_clean"]] += 1
        if row["playerA_faction_clean"]:
            faction_counter[row["playerA_faction_clean"]] += 1
        if row["playerB_faction_clean"]:
            faction_counter[row["playerB_faction_clean"]] += 1

        cleaned.append(row)

    return cleaned, system_counter, player_counter, faction_counter

def write_csv(output_file, fieldnames, rows):
    extra_fields = [
        "season_year",
        "normalized_played_on", "normalized_result",
        "playerA_battle_ready", "playerB_battle_ready",
        "playerA_faction_clean", "playerB_faction_clean",
        "playerA_user_clean", "playerB_user_clean"
    ]

    fieldnames = fieldnames + extra_fields
    with open(output_file, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def report(system_counter, player_counter, faction_counter, cleaned):
    print("=== Summary Report ===")
    print("\nGames per System:")
    for system, count in system_counter.items():
        print(f"  {system}: {count}")

    print("\nGames per Player:")
    for player, count in player_counter.items():
        print(f"  {player}: {count}")

    print("\nFactions Appeared:")
    for faction, count in faction_counter.items():
        print(f"  {faction}: {count}")

    # Battle ready stats
    battle_ready_a = sum(1 for row in cleaned if row["playerA_battle_ready"] == 1)
    battle_ready_b = sum(1 for row in cleaned if row["playerB_battle_ready"] == 1)
    print("\nBattle Ready Stats:")
    print(f"  Player A battle ready in {battle_ready_a} games")
    print(f"  Player B battle ready in {battle_ready_b} games")

# ---------------- CLI Entry ----------------
def main():
    parser = argparse.ArgumentParser(description="Clean raw game CSV files.")
    parser.add_argument("input_file", help="Path to raw input CSV file")
    parser.add_argument("output_file", help="Path to cleaned output CSV file")
    args = parser.parse_args()

    fieldnames, rows = read_csv(args.input_file)
    cleaned, system_counter, player_counter, faction_counter = clean_rows(rows)
    write_csv(args.output_file, fieldnames, cleaned)
    report(system_counter, player_counter, faction_counter, cleaned)
    print(f"\nCleaned file saved as {args.output_file}")

if __name__ == "__main__":
    main()
