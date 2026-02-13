# Quick Start: Import Your Game Data

## Your CSV Format ✓

Your CSV format is **correct**! Here's what you have:

```csv
system_id;date;player_one;score_one;player_two;score_two
2;2024/12/31;Madison L;17;Andrew B;-17
2;2024/12/30;Eugen_M;14;James W;-14
```

**Good to know:**

- ✓ Using semicolons (`;`) as delimiter - **now supported**
- ✓ All required columns present
- ✓ Dates in `YYYY/MM/DD` format - **supported**
- ✓ Scores can be negative - **supported**

---

## 3-Step Workflow

### Step 1: Extract Unique Players

Run this script to pull all unique player names from your games CSV:

```bash
python tools/extract_players.py --input games.csv --output players.csv
```

**What it does:**

- Reads your games CSV
- Finds all unique player names
- Creates `players.csv` with all names
- Auto-detects semicolon or comma delimiter

**Output:**

```csv
old_name,username
Andrew B,Andrew B
Eugen_M,Eugen_M
James W,James W
Madison L,Madison L
Maxim B,Maxim B
Rachel W,Rachel W
Ruben M,Ruben M
Jason V,Jason V
Darryn P,Darryn P
```

### Step 2: Edit Player Mapping (if needed)

Edit `players.csv` if the usernames in your database are different from the names in your games CSV.

**Example:** If a player named "Madison L" in games is actually username "madison_lewis" in database:

Change:

```csv
Madison L,Madison L
```

To:

```csv
Madison L,madison_lewis
```

**Important:** The `username` column must match actual usernames in the database!

### Step 3: Preview and Import

Preview changes (no database modifications):

```bash
python tools/import_games.py --data games.csv --mapping players.csv --dry-run
```

Run the actual import:

```bash
python tools/import_games.py --data games.csv --mapping players.csv
```

---

## For Your Data

Here's the exact workflow for your CSV:

```bash
# Step 1: Extract players
python tools/extract_players.py --input games.csv --output players.csv

# Step 2: (Edit players.csv if needed in text editor)

# Step 3: Preview
python tools/import_games.py --data games.csv --mapping players.csv --dry-run

# Step 4: Import
python tools/import_games.py --data games.csv --mapping players.csv
```

---

## What Gets Created

From your 5 games, the import will create:

| Item             | Details                                       |
| ---------------- | --------------------------------------------- |
| **Games**        | 5 game records                                |
| **Location**     | "Imported Games" (auto-created)               |
| **Factions**     | "TBD (Warhammer 40,000)" (auto-created)       |
| **Players**      | Looking up 9 unique players from your mapping |
| **Points Band**  | 2000 for all games                            |
| **Battle Ready** | False (0) for all players                     |

---

## Your Players (from your CSV)

```
Andrew B
Darryn P
Eugen_M
James W
Jason V
Madison L
Maxim B
Rachel W
Ruben M
```

Make sure all these usernames exist in the database before importing!

---

## Delimiter Support

Both scripts now auto-detect delimiters:

- ✓ Commas `,`
- ✓ Semicolons `;`

So your CSV with semicolons will work without any changes!

---

## Troubleshooting

**"User 'Madison L' not found in database"**

- User doesn't exist yet
- Create the account in the web UI first
- Or update players.csv to map to correct username

**"No mapping for player 'Madison L'"**

- Typo in players.csv
- Check old_name matches exactly

**"Invalid system_id"**

- Only 1 (Age of Sigmar) or 2 (40k) allowed
- Your CSV uses 2, which is correct

See `IMPORT_GUIDE.md` for more details.
