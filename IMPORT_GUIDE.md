# Game Data Import Tool

This script imports game results from CSV files into the DTC League database.

## Requirements

- Python 3.6+
- SQLite3 (included with Python)
- CSV files with proper format (see below)

## File Formats

### 1. Game Data CSV (`games.csv`)

Required columns: `system_id`, `date`, `player_one`, `score_one`, `player_two`, `score_two`

**Columns:**

- `system_id`: Game system (1 = Age of Sigmar, 2 = Warhammer 40k)
- `date`: Game date (supports multiple formats: `31-Dec-2024`, `12/31/2024`, `2024-12-31`)
- `player_one`: Player 1 name (must match mapping file)
- `score_one`: Player 1 score (integer, can be negative)
- `player_two`: Player 2 name (must match mapping file)
- `score_two`: Player 2 score (integer, can be negative)

**Example:**

```csv
system_id,date,player_one,score_one,player_two,score_two
2,31-Dec-2024,Madison L,17,Andrew B,-17
2,30-Dec-2024,Eugen_M,14,James W,-14
1,23-Oct-2024,Maxim B,8,Darryn P,-8
```

### 2. Player Mapping CSV (`players.csv`)

Required columns: `old_name`, `username`

Maps the names in your game data to actual usernames in the database.

**Columns:**

- `old_name`: Name from your game data CSV
- `username`: Matching username in the database (must exist in `users` table)

**Example:**

```csv
old_name,username
Madison L,Madison L
Andrew B,Andrew B
Eugen_M,Eugen_M
James W,James W
```

## Usage

### Basic Import (with dry-run)

```bash
python tools/import_games.py --data games.csv --mapping players.csv --dry-run
```

This previews what would be imported without making changes.

### Actual Import

```bash
python tools/import_games.py --data games.csv --mapping players.csv
```

This imports the data and commits to the database.

## Features

- ✓ Validates all required data before importing
- ✓ Auto-creates "TBD" factions if needed
- ✓ Auto-creates "Imported Games" location if needed
- ✓ Determines game results from scores (higher score wins)
- ✓ Sets default 2000 points for all games
- ✓ Sets Battle Ready status to false (not painted/WYSIWYG)
- ✓ Wraps operations in transactions for safety
- ✓ Dry-run mode to preview changes
- ✓ Detailed console logging and error reporting

## How Results are Determined

Results are calculated from the scores:

- **Higher score wins**: Player with higher score gets "win", opponent gets "loss"
- **Equal scores**: Both players get "draw"
- Player 1 and Player 2 row order doesn't matter

## Auto-Created Data

The script will automatically create:

1. **Location**: "Imported Games" (if it doesn't exist)
2. **Factions**: "TBD (Age of Sigmar)" or "TBD (Warhammer 40,000)" (if needed)
3. **ELO Rules**: For 2000-point games (if needed)

## Error Handling

The script skips rows with:

- Invalid system_id (not 1 or 2)
- Missing or unparseable dates
- Missing player names
- Players not found in mapping file
- Players not found in database
- Invalid scores

All errors are logged to console with row numbers.

## Example Output

```
Loading player mapping...
  Loaded 8 player mappings

Processing example_games.csv...

Row 2:
  ✓ Imported game 142: Madison L vs Andrew B

Row 3:
  ✓ Imported game 143: Eugen_M vs James W

Row 4:
  ✓ Imported game 144: Ruben M vs Jason V

Row 5:
  ✓ Imported game 145: Maxim B vs Darryn P

============================================================
IMPORT SUMMARY
============================================================
Total rows processed: 4
Successfully imported: 4
Failed imports: 0
Skipped rows: 0

New factions created: 1
  - TBD (Warhammer 40,000)

Changes committed to database
```

## Troubleshooting

### "User 'John Doe' not found in database"

- Check that the username exists in the database
- Verify the player mapping CSV has the correct mapping
- Create the user account in the web UI first

### "No mapping for player 'John Doe'"

- Add the mapping to your `players.csv` file
- Make sure the `old_name` exactly matches the game data CSV

### "Invalid system_id"

- Use 1 for Age of Sigmar or 2 for Warhammer 40k
- Check your system_id column values

### Partial Import Failed

- The script uses transactions, so if an error occurs, that row is skipped
- Check the console output for the specific error message
- Correct the issue and re-run the import for the problematic row

## Testing

Use the included example files to test:

```bash
python tools/import_games.py --data example_games.csv --mapping example_players.csv --dry-run
```

Then check the output before running without `--dry-run`.
