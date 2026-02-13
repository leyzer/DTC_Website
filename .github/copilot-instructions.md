<!-- Copilot instructions for codebase contributors and AI agents -->

# Project-specific guidance for AI coding agents

This repository is a small Flask web app that uses SQLite (file-based DB) and server-side sessions. Below are concise, actionable notes to help an AI agent be immediately productive.

- Architecture & entrypoint:

  - Single Flask app in `server.py` (entrypoint: `if __name__ == "__main__": app.run(debug=True)`).
  - Templates live in `templates/` (examples: `index.html`, `league.html`, `login.html`, `register.html`).
  - Static CSS in `static/styles.css`.

- Data layer and conventions:

  - Uses `sqlite3` directly (no ORM). Primary DB file seen in code: `GPTLeague.db` (ensure this file exists in project root).
  - Some helper functions reference `league.db` (see `helpers.py::CURRENT_YEAR()`): treat this as an inconsistency — prefer `GPTLeague.db` unless tests show otherwise.
  - Common table names: `users`, `games`, `results`, `generalship`, `seasons`, `rating_table`, `factions`.
  - SQL parameters are used with `?` placeholders; maintain this parameterized style to avoid injection.

- Authentication & sessions:

  - Passwords hashed with `bcrypt` via `helpers.hash_password()` and verified via `helpers.check_password()`.
  - `helpers.check_account()` currently queries `user_name` column while `server.py` frequently uses `username` — double-check column names before editing authentication logic.
  - Sessions are configured to use filesystem storage in `server.py` (`SESSION_TYPE = "filesystem"`) via `flask_session`.

- Dependencies & run instructions:
  - `requirements.txt` only lists `Flask` but code uses `flask_session`, `bcrypt`, and `plotly` — install the environment from `prod/` venv or run:

```powershell
python -m pip install -r requirements.txt
python -m pip install flask_session bcrypt plotly
python server.py
```

- Patterns and coding conventions:

  - Routes perform SQL queries and data assembly inline — prefer minimal, targeted refactors when changing query logic.
  - Use `with sqlite3.connect(...) as connection:` blocks (existing pattern) to ensure connections close.
  - Helper utilities live in `helpers.py` (examples: `login_required`, `apology`, `CURRENT_YEAR`, `season`, `all_seasons`). Reuse these helpers instead of duplicating logic.

- Notable inconsistencies to watch for (fix cautiously):

  - DB filename mismatch: `GPTLeague.db` vs `league.db`.
  - User column names: `username` vs `user_name`; `id` vs `user_id` appear interchangeably in comments and queries.
  - `helpers.check_account()` expects hashed password in different column index ordering; confirm schema before modifying.

- Where to look for examples:

  - Authentication flow: `server.py` `login()`, `register()`, `reset_password()`.
  - Core domain logic and scoring: `server.py` `home()` and `league()` compute `generalship`, `social`, `hobby`, and `score` using many SQL aggregates.
  - Helper utilities: `helpers.py`.

- When making changes:
  - Run the app locally with `python server.py` (debug mode is enabled in main).
  - Verify DB schema and presence of `GPTLeague.db` before running migrations or schema edits.
  - Prefer small incremental changes: update one route or helper, run, and manually smoke-test the corresponding page (templates exist for each route).

If anything here is unclear or you want additional examples (SQL schema, sample DB, or walk-through for a specific route), tell me which area to expand.
