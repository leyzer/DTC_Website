# Super Easy Import: Both Data Formats Support

## The New Way (Just One Command!)

You now have a **unified import tool** that handles BOTH data formats automatically:

```bash
python tools/auto_import.py --data games.csv
```

That's it! It auto-detects the format and handles everything.

---

## What It Does Automatically

✓ **Auto-creates missing users** with temporary passwords
✓ **Uses real faction names** from your data (no more "TBD")
✓ **Auto-creates factions** if they don't exist
✓ **Activates players in system** - Players are automatically marked as active members of the game system
✓ **Detects both formats** automatically (Format 1 or Google Form)
✓ **Sets battle-ready status** from checkboxes (Format 2 only)
✓ **Parses results correctly** from your data
✓ **Shows temporary passwords** for new users
✓ **Dry-run mode** to preview changes

---

## Your Two Data Formats

### Format 1: Simple CSV (Your game history)

```csv
system_id;date;player_one;score_one;player_two;score_two
2;2024/12/31;Madison L;17;Andrew B;-17
2;2024/12/30;Eugen_M;14;James W;-14
```

### Format 2: Google Form Responses

```
Timestamp;What game system did you play?;When was the game played?;...;Player A (person submitting the result);...;Player A Army;Player B (your opponent);...;Player B Army
2/14/2025 7:09:09;Warhammer 40,000;2025/02/12;...;Brandon W;...;Drukhari;Robert N;...;Tyranids
```

---

## One-Step Import

### Step 1: Use the import command

**Preview changes first (recommended):**

```bash
python tools/auto_import.py --data games.csv --dry-run
```

**Run the actual import:**

```bash
python tools/auto_import.py --data games.csv
```

That's all you need!

---

## What Happens

### Auto-Created Users

If a player doesn't exist in the database:

- Username: Their name from the CSV
- Temporary password: `TempPassword123!`
- Status: Active and ready to use

**Example output:**

```
New users created: 3
WARNING: Set passwords for these users!
  - Brandon W (temp: TempPassword123!)
  - Robert N (temp: TempPassword123!)
  - Alex W (temp: TempPassword123!)
```

These users can log in and should change their passwords immediately.

### Auto-Created Factions (Format 2 only)

Real faction names from your form:

```
New factions created: 2
  - Drukhari
  - Tyranids
```

No more "TBD" factions!

### Auto-Activated System Members

When you import a game:
- **Both players are automatically marked as active members** of that game system
- If a player already has a membership that was inactive, it gets activated
- If a player doesn't have a membership yet, one is created with active status
- This means imported players will show up in the system membership management page

Example: If you import a Warhammer 40,000 game between "Alice" and "Bob", both Alice and Bob become **active members** of the Warhammer 40,000 system.

### User Sets Battle Ready (Format 2 only)

- If both "Painted" AND "WYSIWYG" are checked: ✓ Battle Ready
- Otherwise: Not battle ready

---

## Full Workflow

```bash
# Step 1: Ensure you have your CSV file ready (games.csv)
# Step 2: Preview the import
python tools/auto_import.py --data games.csv --dry-run

# Step 3: Check the preview output
# Step 4: Run the actual import
python tools/auto_import.py --data games.csv

# Step 5: Users see summary with any new user passwords
# Step 6: Optional: Reset passwords for new users in the web UI
```

---

## Example Run

```
Detected delimiter: ';'
Detected format: Format 2

Processing games.csv...

Row 2:
  ✓ Imported: Brandon W vs Robert N
Row 3:
  ✓ Imported: Madison L vs Brandon W

======================================================================
IMPORT SUMMARY
======================================================================
Format: 2
Successfully imported: 2
Failed imports: 0
Skipped rows: 0

New users created: 1
WARNING: Set passwords for these users!
  - Robert N (temp: TempPassword123!)

New factions created: 2
  - Drukhari
  - Tyranids

Changes committed to database
```

---

## Error Handling

The script gracefully handles problems:

| Issue                | What Happens                                           |
| -------------------- | ------------------------------------------------------ |
| Invalid date         | Row skipped, warning shown                             |
| Unknown system       | Row skipped (e.g., if format 2 has unsupported system) |
| Missing player name  | Row skipped                                            |
| Missing faction name | Row skipped                                            |
| Invalid result       | Row skipped                                            |

All errors are logged to the console with row numbers.

---

## Key Differences: Format 1 vs Format 2

| Feature       | Format 1                    | Format 2                |
| ------------- | --------------------------- | ----------------------- |
| Faction       | Auto-creates "TBD (System)" | Uses real faction names |
| Battle Ready  | Always false                | From Painted + WYSIWYG  |
| Result        | Calculated from scores      | From result field       |
| User Creation | Yes                         | Yes                     |
| Typical Use   | Historical data             | New form submissions    |

---

## That's It!

You have one simple command for both data formats:

```bash
python tools/auto_import.py --data games.csv
```

- Preview first with `--dry-run`
- Users auto-created with temp passwords
- Factions auto-created with real names
- Battle-ready status handled correctly
- Everything logged to console

No mapping files, no manual setup, no complexity. Just import!
