# DTC Warhammer 40k League - Codebase Overview

## Project Description

A Flask-based web application for managing a local Warhammer 40k league. Players track game results, faction statistics, personal stats, and competitive rankings. The scoring system comprises three main categories:

- **Generalship** (40 pts): Ranking-based from games played
- **Hobby** (20 pts): Painting (10) + WYSIWYG compliance (10)
- **Social** (40 pts): Games Played (10) + Unique Opponents (30)

---

## Architecture Overview

### Entry Point

- **server.py** - Main Flask application initialization
  - Scoring constants defined as module variables
  - Context processors inject systems and current user into all templates
  - Routes registered via blueprints from `routes/` package
  - Session management: filesystem-based via `flask_session`
  - Debug mode controlled via `FLASK_ENV` environment variable

### Database

- **SQLite** file-based: `GPTLeague.db` (must exist in project root)
- No ORM - raw `sqlite3` with parameterized queries (`?` placeholders)
- Connections use context managers: `with sqlite3.connect('GPTLeague.db') as conn:`
- Schema defined in `schema.sql` (see Database Schema section below)

### Dependencies

```
Flask==3.0.0
Flask-Session==0.8.0
bcrypt==4.1.2
plotly==5.19.0
```

---

## Database Schema

### Core User Tables

#### `users`

```
user_id (INTEGER PRIMARY KEY)
user_name (TEXT UNIQUE) - login username, stored lowercase
full_name (TEXT)
email (TEXT UNIQUE)
password_hash (TEXT) - bcrypt hash
is_active (INTEGER DEFAULT 1)
is_provisional (INTEGER DEFAULT 0) - for bulk-uploaded users claiming accounts
created_at (TEXT) - ISO datetime
```

#### `user_roles`

```
user_id (INTEGER FK → users.user_id)
role (TEXT) - 'admin' or 'player'
PRIMARY KEY (user_id, role)
```

#### `password_reset_tokens`

```
token_id (INTEGER PRIMARY KEY)
user_id (INTEGER FK → users.user_id)
token (TEXT UNIQUE)
created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
expires_at (TIMESTAMP)
used (INTEGER DEFAULT 0)
```

### League & Membership Tables

#### `seasons`

```
season_id (INTEGER PRIMARY KEY)
name (TEXT) - e.g., "2026 League"
year (INTEGER)
start_date (TEXT) - ISO date
end_date (TEXT) - ISO date
status (TEXT) - 'active' or 'archived'
```

#### `club_memberships`

```
membership_id (INTEGER PRIMARY KEY)
season_id (INTEGER FK → seasons.season_id)
user_id (INTEGER FK → users.user_id)
is_member (INTEGER DEFAULT 1)
UNIQUE(season_id, user_id)
```

#### `systems`

```
system_id (INTEGER PRIMARY KEY)
system_code (TEXT UNIQUE) - e.g., 'AOS', '40K', 'BB', 'KT', etc.
system_name (TEXT)
category (TEXT CHECK) - 'AOS', '40k', 'skirmish', 'mass_battle'
```

#### `system_memberships`

```
membership_id (INTEGER PRIMARY KEY)
user_id (INTEGER FK → users.user_id)
system_id (INTEGER FK → systems.system_id)
joined_on (TEXT DEFAULT now)
is_active (INTEGER DEFAULT 1)
UNIQUE(user_id, system_id)
```

### Game & Faction Tables

#### `games`

```
game_id (INTEGER PRIMARY KEY)
season_id (INTEGER FK → seasons.season_id)
system_id (INTEGER FK → systems.system_id)
played_on (TEXT) - ISO datetime
location_id (INTEGER FK → locations.location_id, nullable)
points_band (TEXT) - e.g., '1000', '2000', 'SP/CP', 'skirmish'
notes (TEXT)
score (INTEGER)
ignored (INTEGER) - flag for excluded games
```

#### `game_participants`

```
game_id (INTEGER FK → games.game_id)
player_id (INTEGER FK → users.user_id)
faction_id (INTEGER FK → factions.faction_id, nullable)
result (TEXT CHECK) - 'win', 'loss', 'draw'
painting_battle_ready (INTEGER 0/1)
score_raw (INTEGER) - optional mission VP
PRIMARY KEY (game_id, player_id)
```

#### `factions`

```
faction_id (INTEGER PRIMARY KEY)
system_id (INTEGER FK → systems.system_id)
faction_name (TEXT)
UNIQUE(system_id, faction_name)
```

#### `locations`

```
location_id (INTEGER PRIMARY KEY)
name (TEXT) - e.g., "Top Deck", "Musgrave Hall"
location_type (TEXT CHECK) - 'store', 'other', 'tournament'
city (TEXT)
notes (TEXT)
```

### Ratings Tables

#### `ratings`

```
player_id (INTEGER FK → users.user_id)
season_id (INTEGER FK → seasons.season_id)
system_id (INTEGER FK → systems.system_id)
current_rating (INTEGER)
last_updated (TEXT)
PRIMARY KEY (player_id, season_id, system_id)
```

#### `rating_history`

```
game_id (INTEGER FK → games.game_id)
player_id (INTEGER FK → users.user_id)
system_id (INTEGER FK → systems.system_id)
old_rating (INTEGER)
new_rating (INTEGER)
k_factor_used (INTEGER)
expected_score (REAL)
actual_score (REAL)
PRIMARY KEY (game_id, player_id, system_id)
```

#### `elo_rules`

```
elo_rule_id (INTEGER PRIMARY KEY)
category (TEXT CHECK) - 'AOS', '40k', 'skirmish', 'mass_battle'
points_band (TEXT) - points value or category
base_rating (INTEGER DEFAULT 400)
k_factor (INTEGER) - K-factor for ELO calculation
UNIQUE(category, points_band)
```

---

## Routes & Blueprints

### Blueprint Registration

Registered in `routes/__init__.py` → `register_blueprints(app)` called in `server.py`

### `routes/auth.py` - Authentication Blueprint

| Route              | Methods   | Auth    | Purpose                                           |
| ------------------ | --------- | ------- | ------------------------------------------------- |
| `/login`           | GET, POST | —       | User login                                        |
| `/logout`          | GET       | ✓       | Clear session, redirect home                      |
| `/register`        | GET, POST | —       | User registration (uses full form validation)     |
| `/reset_password`  | GET, POST | ✓       | Change password for logged-in user                |
| `/forgot_password` | GET, POST | —       | Disabled (redirects to login with message)        |
| `/reset/<token>`   | GET, POST | —       | Disabled (redirects to login with message)        |
| `/claim_account`   | GET, POST | —       | Claim provisional account with temp password      |
| `/endseason`       | GET, POST | ✓ Admin | Archive current season, create next year's season |

**Key Functions:**

- `login()` - Validates username/password, sets `session['user_id']`
- `register()` - Full registration with email, password validation, auto-assign admin to first user
- `reset_password()` - Logged-in user password change
- `claim_account()` - For users pre-created by admin (provisional=1): verify temp password, set new password
- `endseason()` - Admin-only: archive season, create new season for next year

### `routes/main.py` - Core Pages Blueprint

| Route             | Methods   | Auth | Purpose                                      |
| ----------------- | --------- | ---- | -------------------------------------------- |
| `/`               | GET, POST | —    | Redirect to `/overall` (league standings)    |
| `/elo_ratings`    | GET, POST | —    | ELO ratings by system (with year filter)     |
| `/about`          | GET       | —    | About page                                   |
| `/contact`        | GET, POST | —    | Contact form                                 |
| `/profile`        | GET, POST | ✓    | User profile, password reset, admin controls |
| `/people`         | GET       | —    | Player directory                             |
| `/events`         | GET       | —    | League events list                           |
| `/documents`      | GET       | —    | Document repository                          |
| `/league_formats` | GET       | —    | League format info                           |

### `routes/leagues.py` - Game Management Blueprint

| Route               | Methods   | Auth | Purpose                                       |
| ------------------- | --------- | ---- | --------------------------------------------- |
| `/league`           | GET, POST | ✓    | Record game result, select system             |
| `/league/<game_id>` | GET       | —    | View game details                             |
| `/gamesPlayed`      | GET, POST | —    | List all games with filters (verified status) |

**Key Functions:**

- `league()` - Game entry form; validates players, factions, location; updates ELO ratings
- `gamesPlayed()` - Display games with win/loss/draw visualization

### `routes/stats.py` - Statistics & Analytics

| Route            | Methods   | Auth | Purpose                                                         |
| ---------------- | --------- | ---- | --------------------------------------------------------------- |
| `/factionstats`  | GET, POST | —    | Faction win/loss/draw stats with Plotly pie charts              |
| `/playerstats`   | GET, POST | —    | Individual player game record, W/L/D by faction                 |
| `/overall`       | GET, POST | —    | League standings (season filter, green highlight for 10+ games) |
| `/store_reports` | GET, POST | —    | Location-based game reports                                     |

**Key Functions:**

- `factionstats()` - Aggregates faction performance across games; generates Plotly JSON for pie charts
- `playerstats()` - Player-specific stats (W/L/D by faction, game history)
- `overall()` - Main leaderboard; computes composite score from Generalship, Hobby, Social

### `routes/admin.py` - Admin Management

| Route                          | Methods   | Auth    | Purpose                                     |
| ------------------------------ | --------- | ------- | ------------------------------------------- |
| `/manageMemberships`           | GET, POST | ✓ Admin | Toggle club membership by season            |
| `/updateMemberships`           | POST      | ✓ Admin | Batch update memberships                    |
| `/toggleMembership`            | POST      | ✓ Admin | AJAX membership toggle                      |
| `/admin_manage_users`          | GET, POST | ✓ Admin | List/search users, manage roles             |
| `/batch_upload`                | GET, POST | ✓ Admin | CSV bulk user import (provisional accounts) |
| `/batch_upload_users_complete` | GET       | ✓ Admin | Display temp passwords for new bulk users   |
| `/admin_club_memberships`      | GET, POST | ✓ Admin | Manage club membership settings             |
| `/admin_system_memberships`    | GET, POST | ✓ Admin | Manage system-level memberships             |
| `/export_data`                 | GET, POST | ✓ Admin | Export database as SQL dump or CSV files    |
| `/endseason`                   | GET, POST | ✓ Admin | (See auth.py)                               |

---

## Key Helper Functions (helpers.py)

### Authentication

- `hash_password(password)` - bcrypt hash (uses `bcrypt.hashpw`)
- `check_password(password, hashed_password)` - bcrypt verify
- `check_account(username, password)` - Query user by username, verify password hash
- `validate_password_strength(password)` - Returns (bool, msg); requires 8+ chars, 1 uppercase, 1 lowercase, 1 digit
- `login_required(f)` - Decorator; redirects to `/login` if `session['user_id']` is None
- `is_admin(user_id)` - Check if user has 'admin' role

### Database

- `CURRENT_YEAR()` - Return `MAX(year)` from `seasons` table
- `season(year)` - Return (start_date, end_date) tuple for given year
- `all_seasons()` - Return all seasons with status='active' or 'archived', ordered by year DESC

### Utilities

- `apology(message, code)` - Render `apology.html` template with error message
- `is_valid_email(email)` - Regex validation for email format

---

## Template Structure

### Layout (`templates/layout.html`)

- Base template for all pages
- Navigation bar (visible/hidden based on login status)
- Breadcrumb navigation
- Flash message container
- Dark mode toggle
- Context variables: `current_user` (dict with `user_id`, `user_name`, `is_admin`), `systems` (list of all systems)

### Key Templates

| Template                  | Purpose                                   |
| ------------------------- | ----------------------------------------- |
| `login.html`              | Login form                                |
| `register.html`           | User registration form                    |
| `profile.html`            | User profile, password reset, admin panel |
| `claim_account.html`      | Claim provisional account                 |
| `league.html`             | Game result entry form                    |
| `gamesPlayed.html`        | Game history listing                      |
| `overall.html`            | League standings/leaderboard              |
| `factionstats.html`       | Faction statistics with charts            |
| `playerstats.html`        | Player-specific stats                     |
| `elo_ratings.html`        | System-wide ELO ratings                   |
| `manageMemberships.html`  | Admin: manage club memberships            |
| `admin_manage_users.html` | Admin: user list and roles                |
| `batch_upload_users.html` | Admin: CSV import interface               |
| `export_data.html`        | Admin: database export (SQL/CSV)          |
| `apology.html`            | Error page template                       |

---

## Scoring System

### Constants (server.py)

```python
MAXVALUE_PAINTED = 10
MAXVALUE_WYSIWYG = 10
MAXVALUE_GENERALSHIP = 40
MAXVALUE_GAMESPLAYED = 10
MAXVALUE_UNIQUE = 30
```

### Composite Score Breakdown

1. **Generalship** (40 pts)
   - Top player → 40 pts
   - Others → proportional based on ELO ranking

2. **Hobby** (20 pts)
   - **Painting** (10 pts): % of games played fully painted
   - **WYSIWYG** (10 pts): % of games with WYSIWYG armies

3. **Social** (40 pts)
   - **Games Played** (10 pts): % of games relative to leader
   - **Unique Opponents** (30 pts): count of distinct opponents faced

**Qualification:** Green highlight on leaderboard after 10+ games in a season

---

## ELO Rating System

### Files

- `ratings.py` - ELO calculation logic (not fully shown in overview read, but referenced in routes)
- `elo_rules` table - K-factors by category and points_band

### Flow

1. Game recorded in `games` table
2. `game_participants` entries created for each player
3. `ratings.update_ratings_for_season()` called after game submission
4. New ratings computed based on K-factor from `elo_rules`
5. `ratings` table updated; `rating_history` logged

---

## Notable Code Patterns & Conventions

### Database Connections

```python
# Standard pattern - always use context manager
with sqlite3.connect('GPTLeague.db') as connection:
    connection.row_factory = sqlite3.Row  # Optional; enables dict-like row access
    cursor = connection.cursor()
    result = cursor.execute("SELECT ... FROM ... WHERE ... = ?", (param_value,)).fetchone()
    connection.commit()  # For INSERT/UPDATE/DELETE
```

### Parameter Binding

- Always use `?` placeholders with tuple arguments: `("SELECT ... WHERE col = ?", (value,))`
- Never f-string SQL to prevent injection

### Flash Messages

```python
flash("Success message", "success")      # Bootstrap alert-success
flash("Warning message", "warning")      # Bootstrap alert-warning
flash("Error message", "danger")         # Bootstrap alert-danger
```

### Response Patterns

```python
# Render template
return render_template("template.html", var1=val1, var2=val2)

# Redirect
return redirect("/path") or redirect(url_for("blueprint.route_name"))

# Error
return apology("Error message", 400)
```

---

## Deployment Notes

### Environment Variables

- `FLASK_ENV` - 'development' or 'production' (enables/disables debug mode)
- `DEFAULT_USERNAME`, `DEFAULT_PASSWORD` - For future default user initialization

### File Structure

- `GPTLeague.db` - Must exist in project root with proper schema
- `flask_session/` - Auto-created; stores filesystem sessions
- `static/` - CSS files (`styles.css`, `dtc_colors.css`)
- `templates/` - Jinja2 HTML templates
- `data_exports/` - CSV data dumps

### Running

```powershell
python server.py
# Runs on http://localhost:5000 with debug mode if FLASK_ENV=development
```

---

## Common Queries & Patterns

### Get current logged-in user

```python
user_id = session.get("user_id")  # Returns None if not logged in
```

### Check if user is admin

```python
from helpers import is_admin
if is_admin(session["user_id"]):
    # Admin block
```

### Get current season

```python
from helpers import CURRENT_YEAR
year = CURRENT_YEAR()
season_row = cursor.execute("SELECT season_id FROM seasons WHERE year = ?", (year,)).fetchone()
season_id = season_row["season_id"]
```

### Fetch user info

```python
user = cursor.execute(
    "SELECT user_id, user_name, full_name, email FROM users WHERE user_name = ?",
    (username,)
).fetchone()
```

### Insert new user

```python
from helpers import hash_password
hashed = hash_password(new_password)
cursor.execute(
    "INSERT INTO users (user_name, full_name, email, password_hash) VALUES (?,?,?,?)",
    (username, full_name, email, hashed)
)
cursor.execute(
    "INSERT INTO user_roles (user_id, role) VALUES (?,?)",
    (user_id, "admin" or "player")
)
connection.commit()
```

---

## Initial Setup & First User Registration

### Registration Availability

- **Registration form** is visible on `/login` page **only if no users exist** in the database
- Once the first user is registered, the registration form is automatically hidden for all subsequent users
- This ensures controlled user creation - future users must be created by administrators

### First User Becomes Admin

- The first registered user is automatically assigned the **'admin' role**
- This allows them to:
  - Create additional user accounts (via admin panel)
  - Manage league memberships and settings
  - Access admin features like batch user import
  - Assign admin roles to other users

### Subsequent User Creation

- After first user setup, additional users are created by admins through:
  - `/admin_manage_users` - Manual user creation
  - `/batch_upload` - CSV bulk import (creates provisional accounts)

---

## Data Export Feature

### Access

- **Route**: `/export_data` (admin-only)
- **Auth**: Requires 'admin' role
- **Permission check**: Redirects to home if user is not admin

### Export Formats

#### SQL Dump

- **File**: `dtc_league_backup_sql_YYYYMMDD_HHMMSS.zip`
- **Contents**: Complete SQLite database as SQL statements
- **Use cases**:
  - Complete backup for disaster recovery
  - Server migration/relocation
  - Exact point-in-time snapshot
- **Restore process**:
  ```bash
  sqlite3 new_database.db < dtc_league_dump_YYYYMMDD_HHMMSS.sql
  ```

#### CSV Export

- **File**: `dtc_league_backup_csv_YYYYMMDD_HHMMSS.zip`
- **Contents**: Separate CSV file for each database table
- **Use cases**:
  - Data analysis in Excel or Google Sheets
  - Manual review of specific tables
  - Selective data restoration
- **Included tables**: All tables except SQLite internal tables (sqlite\_\*)

### Export Details

- **ZIP Archive**: All exports are automatically compressed
- **Timestamp**: Included in filename for version control
- **README**: Each export includes restore instructions
- **Logging**: Admin exports logged with user ID
- **Security**: Keep backups in secure location

---

## Known Issues & Inconsistencies

1. **Database filename mismatch** - Code references both `GPTLeague.db` and legacy `league.db`; prefer `GPTLeague.db`
2. **User column naming** - Uses both `user_name` and `username` in comments; actual column is `user_name`
3. **Password reset disabled** - `/forgot_password` and `/reset/<token>` routes are disabled; users must contact admin
4. **Provisional accounts** - Users can be bulk-created with `is_provisional=1`; they claim via `/claim_account`

---

## Future Development Ideas

- Enable self-serve password reset with token verification
- Implement more advanced ELO categories
- Add tournament mode and brackets
- Create mobile-friendly views
- Add real-time notifications for new games

---

**Last Updated:** February 22, 2026
**Version:** 1.0
