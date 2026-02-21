"""Admin and membership management routes."""
import sqlite3
import csv
import io
import string
import secrets
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from helpers import is_admin, login_required, CURRENT_YEAR, season, hash_password, is_valid_email
from ratings import update_ratings_for_season

admin_bp = Blueprint('admin', __name__)


@admin_bp.route("/manageMemberships", methods=["GET", "POST"])
@login_required
def manage_memberships():
    user_id = session["user_id"]
    
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        selected_year = request.args.get("season") or CURRENT_YEAR()
        season_row = cursor.execute("SELECT season_id FROM seasons WHERE year = ?", (selected_year,)).fetchone()
        if not season_row:
            flash("Season not found", "warning")
            return redirect(url_for("admin.manage_memberships"))
        season_id = season_row["season_id"]

        seasons = cursor.execute("SELECT season_id, year FROM seasons WHERE status IN ('active','archived') ORDER BY year DESC").fetchall()

        users = cursor.execute("""
            SELECT u.user_id, u.user_name, u.full_name,
                COALESCE(cm.is_member, 0) AS is_member
            FROM users u
            LEFT JOIN club_memberships cm
            ON cm.user_id = u.user_id AND cm.season_id = ?
            ORDER BY u.full_name
        """, (season_id,)).fetchall()

    return render_template("manageMemberships.html",
                            seasons=seasons,
                            selected_year=selected_year,
                            users=users)


@admin_bp.route("/updateMemberships", methods=["POST"])
@login_required
def updateMemberships():
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to update memberships.", "danger")
        return redirect("/")

    selected_year = request.form.get("season")
    with sqlite3.connect("GPTLeague.db") as connection:
        cursor = connection.cursor()
        season_row = cursor.execute("SELECT season_id FROM seasons WHERE year = ?", (selected_year,)).fetchone()
        if not season_row:
            flash("Season not found", "warning")
            return redirect(url_for("admin.manage_memberships"))
        season_id = season_row[0]

        members = request.form.getlist("members[]")
        all_users = cursor.execute("SELECT user_id FROM users").fetchall()
        for (uid,) in all_users:
            is_member = 1 if str(uid) in members else 0
            cursor.execute("""
                INSERT INTO club_memberships (season_id, user_id, is_member)
                VALUES (?, ?, ?)
                ON CONFLICT(season_id, user_id) DO UPDATE SET is_member = excluded.is_member
            """, (season_id, uid, is_member))
        connection.commit()

    flash("Memberships updated", "success")
    return redirect(url_for("admin.manage_memberships", season=selected_year))


@admin_bp.route("/toggleMembership", methods=["POST"])
@login_required
def toggleMembership():
    if not is_admin(session["user_id"]):
        flash("Not authorized", "danger")
        return redirect("/members")

    user_id = request.form.get("user_id")
    season_id = request.form.get("season_id")
    is_member = 1 if request.form.get("is_member") else 0

    with sqlite3.connect('GPTLeague.db') as connection:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO club_memberships (season_id, user_id, is_member)
            VALUES (?, ?, ?)
            ON CONFLICT(season_id, user_id) DO UPDATE SET is_member = excluded.is_member
        """, (season_id, user_id, is_member))
        connection.commit()

    flash("Membership updated", "success")
    return redirect("/members")


@admin_bp.route("/manageSystemMemberships/<int:system_id>", methods=["GET"])
@login_required
def manage_system_memberships(system_id):
    user_id = session["user_id"]

    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        system_row = cursor.execute(
            "SELECT system_name FROM systems WHERE system_id = ?", (system_id,)
        ).fetchone()
        if not system_row:
            flash("System not found", "warning")
            return redirect("/")

        system_name = system_row["system_name"]

        players = cursor.execute("""
            SELECT p.user_id, p.full_name,
                   COALESCE(sm.is_active, 0) AS is_active
            FROM users p
            LEFT JOIN system_memberships sm
            ON sm.user_id = p.user_id AND sm.system_id = ?
            ORDER BY p.full_name
        """, (system_id,)).fetchall()

    return render_template("manageSystemMemberships.html",
                           system_id=system_id,
                           system_name=system_name,
                           players=players)


@admin_bp.route("/admin/memberships", methods=["GET"])
@login_required
def admin_memberships_dashboard():
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        seasons = cursor.execute("SELECT season_id, year FROM seasons ORDER BY year DESC").fetchall()
        systems = cursor.execute("SELECT system_id, system_name FROM systems ORDER BY system_name").fetchall()

    return render_template("admin_memberships_dashboard.html",
                           seasons=seasons,
                           systems=systems)


@admin_bp.route("/admin/updateSystemMemberships/<int:system_id>", methods=["POST"])
@login_required
def update_system_memberships(system_id):
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to update memberships.", "danger")
        return redirect("/")

    members = request.form.getlist("members[]")

    with sqlite3.connect("GPTLeague.db") as conn:
        cursor = conn.cursor()

        all_users = cursor.execute("SELECT user_id FROM users").fetchall()

        for (uid,) in all_users:
            is_active = 1 if str(uid) in members else 0
            cursor.execute("""
                INSERT INTO system_memberships (user_id, system_id, is_active, joined_on)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(user_id, system_id) DO UPDATE SET is_active = excluded.is_active
            """, (uid, system_id, is_active))

        conn.commit()

    flash("System memberships updated successfully", "success")
    return redirect(url_for("admin.admin_system_memberships", system_id=system_id))


@admin_bp.route("/admin/club_memberships", methods=["GET"])
@login_required
def admin_club_memberships():
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        seasons = cursor.execute("SELECT season_id, year FROM seasons ORDER BY year DESC").fetchall()
        selected_year = request.args.get("season") or CURRENT_YEAR()

        season_row = cursor.execute(
            "SELECT season_id FROM seasons WHERE year = ?", (selected_year,)
        ).fetchone()
        if not season_row:
            flash(f"No season found for {selected_year}. Please add it first.", "warning")
            return redirect(url_for("admin.admin_memberships_dashboard"))
        season_id = season_row["season_id"]

        club_users = cursor.execute("""
            SELECT u.user_id, u.user_name, u.full_name,
                   COALESCE(cm.is_member, 0) AS is_member
            FROM users u
            LEFT JOIN club_memberships cm
            ON cm.user_id = u.user_id AND cm.season_id = ?
            ORDER BY u.full_name
        """, (season_id,)).fetchall()

    return render_template("admin_club_memberships.html",
                           seasons=seasons,
                           selected_year=selected_year,
                           club_users=club_users)


@admin_bp.route("/admin/system_memberships/<int:system_id>", methods=["GET"])
@login_required
def admin_system_memberships(system_id):
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        system_row = cursor.execute("SELECT system_name FROM systems WHERE system_id = ?", (system_id,)).fetchone()
        if not system_row:
            flash("System not found", "warning")
            return redirect("/")

        system_name = system_row["system_name"]

        players = cursor.execute("""
            SELECT u.user_id, u.user_name, u.full_name,
                   COALESCE(sm.is_active, 0) AS is_active
            FROM users u
            LEFT JOIN system_memberships sm
            ON sm.user_id = u.user_id AND sm.system_id = ?
            ORDER BY u.full_name
        """, (system_id,)).fetchall()

    return render_template("admin_system_memberships.html",
                           system_id=system_id,
                           system_name=system_name,
                           players=players)


@admin_bp.route("/admin/updateClubMemberships", methods=["POST"])
@login_required
def update_club_memberships():
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to update memberships.", "danger")
        return redirect("/")

    season_id = request.form.get("season")
    members = request.form.getlist("members[]")

    with sqlite3.connect("GPTLeague.db") as conn:
        cursor = conn.cursor()

        all_users = cursor.execute("SELECT user_id FROM users").fetchall()

        for (uid,) in all_users:
            is_member = 1 if str(uid) in members else 0
            cursor.execute("""
                INSERT INTO club_memberships (season_id, user_id, is_member)
                VALUES (?, ?, ?)
                ON CONFLICT(season_id, user_id) DO UPDATE SET is_member = excluded.is_member
            """, (season_id, uid, is_member))

        conn.commit()

    flash("Club memberships updated successfully", "success")
    return redirect(url_for("admin.admin_club_memberships", season=season_id))


@admin_bp.route("/admin/manage_users", methods=["GET", "POST"])
@login_required
def manage_users():
    """Admin page to create and manage users"""
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if request.method == "POST":
            from helpers import hash_password
            
            username = request.form.get("username", "").lower().strip()
            fullname = request.form.get("fullname", "").strip()
            email = request.form.get("email", "").lower().strip()

            # Validation
            if not all([username, fullname, email]):
                flash("Username, full name, and email are required", "warning")
                return redirect(url_for("admin.manage_users"))

            # Check if user exists
            existing = cursor.execute(
                "SELECT user_id FROM users WHERE user_name = ? OR email = ?",
                (username, email)
            ).fetchone()

            if existing:
                flash("Username or email already exists", "warning")
                return redirect(url_for("admin.manage_users"))

            # Generate temporary password
            import secrets
            temp_password = secrets.token_urlsafe(8)
            hashed_password = hash_password(temp_password)

            try:
                cursor.execute(
                    "INSERT INTO users (user_name, full_name, email, password_hash, is_provisional) VALUES (?,?,?,?,?)",
                    (username, fullname.title(), email, hashed_password, 1)
                )
                conn.commit()
                
                flash(f"User created! Username: {username} | Temporary Password: {temp_password} | They can claim their account and change password", "success")
                return redirect(url_for("admin.manage_users"))
            except Exception as e:
                conn.rollback()
                flash(f"Error creating user: {str(e)}", "danger")
                return redirect(url_for("admin.manage_users"))

        # Get all users
        all_users = cursor.execute(
            "SELECT user_id, user_name, full_name, email, is_provisional FROM users ORDER BY user_name"
        ).fetchall()

    return render_template("admin_manage_users.html", users=all_users)


@admin_bp.route("/admin/reset_temp_password/<int:user_id>", methods=["GET"])
@login_required
def reset_temp_password(user_id):
    """Reset and display temporary password for a user"""
    admin_id = session["user_id"]
    if not is_admin(admin_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        user = cursor.execute("SELECT user_id, user_name, full_name, email, is_provisional FROM users WHERE user_id = ?", (user_id,)).fetchone()

        if not user:
            flash("User not found", "danger")
            return redirect(url_for("admin.manage_users"))

        # Generate new temporary password
        from helpers import hash_password
        import secrets
        temp_password = secrets.token_urlsafe(8)
        hashed_password = hash_password(temp_password)

        # Update password
        cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (hashed_password, user_id))
        conn.commit()

    return render_template("temp_password_display.html", user=user, temp_password=temp_password)


@admin_bp.route("/league_settings", methods=["GET", "POST"])
@login_required
def league_settings():
    """Manage league scoring settings."""
    user_id = session["user_id"]
    
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Migrate from old schema if needed
        try:
            cursor.execute("SELECT setting_key FROM league_settings LIMIT 1")
        except:
            # Old table doesn't exist or has wrong schema, drop and recreate
            cursor.execute("DROP TABLE IF EXISTS league_settings")
        
        # Create settings table with new schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_settings (
                setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(season_id, setting_key),
                FOREIGN KEY(season_id) REFERENCES seasons(season_id)
            )
        """)

        # Get list of seasons
        seasons = cursor.execute("SELECT season_id, year FROM seasons WHERE status IN ('active','archived') ORDER BY year DESC").fetchall()
        
        # Get selected year (from POST or default to current year)
        if request.method == "POST":
            selected_year = request.form.get("year")
            opponent_limit = request.form.get("opponent_limit")
            
            if selected_year:
                try:
                    selected_year = int(selected_year)
                    opponent_limit = int(opponent_limit)
                    
                    if opponent_limit < 1:
                        flash("Opponent limit must be at least 1", "danger")
                        return redirect(url_for("admin.league_settings"))
                    
                    # Get season_id for the selected year
                    season_row = cursor.execute("SELECT season_id FROM seasons WHERE year = ?", (selected_year,)).fetchone()
                    if season_row:
                        season_id = season_row["season_id"]
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO league_settings (season_id, setting_key, setting_value, description, updated_at)
                            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (season_id, "opponent_limit", str(opponent_limit), 
                              f"Maximum matches per opponent for {selected_year} (Option A scoring)"))
                        
                        conn.commit()
                        flash(f"Opponent limit for {selected_year} updated to {opponent_limit}", "success")
                    else:
                        flash("Season not found", "danger")
                except ValueError:
                    flash("Year and opponent limit must be numbers", "danger")
            
            return redirect(url_for("admin.league_settings", year=selected_year))

        # Get selected year from query params (default to current year)
        selected_year = request.args.get("year")
        if not selected_year:
            selected_year = CURRENT_YEAR()
        else:
            selected_year = int(selected_year)
        
        # Get setting for selected year
        season_row = cursor.execute("SELECT season_id FROM seasons WHERE year = ?", (selected_year,)).fetchone()
        opponent_limit = 3  # default
        
        if season_row:
            setting_row = cursor.execute("""
                SELECT setting_value FROM league_settings 
                WHERE season_id = ? AND setting_key = 'opponent_limit'
            """, (season_row["season_id"],)).fetchone()
            
            if setting_row:
                opponent_limit = int(setting_row["setting_value"])

    return render_template(
        "league_settings.html",
        seasons=seasons,
        selected_year=selected_year,
        opponent_limit=opponent_limit
    )


@admin_bp.route("/batch_upload", methods=["GET", "POST"])
@login_required
def batch_upload():
    """Batch upload game results from CSV."""
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        systems = cursor.execute(
            "SELECT system_id, system_name, category FROM systems ORDER BY system_name"
        ).fetchall()
        
        locations = cursor.execute(
            "SELECT location_id, name FROM locations ORDER BY name"
        ).fetchall()

    preview_data = None
    errors = []

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected", "warning")
            return redirect(url_for("admin.batch_upload"))

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "warning")
            return redirect(url_for("admin.batch_upload"))

        if not file.filename.endswith(".csv"):
            flash("Please upload a CSV file", "warning")
            return redirect(url_for("admin.batch_upload"))

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
            csv_data = list(csv.DictReader(stream))
            
            if not csv_data:
                flash("CSV file is empty", "warning")
                return redirect(url_for("admin.batch_upload"))

            # Required columns
            if csv_data and csv_data[0]:
                required = {"system_name", "date", "player_one", "player_two", "p1_faction", "p2_faction", "result", "location", "points_band"}
                if not required.issubset(set(csv_data[0].keys())):
                    flash(f"CSV missing required columns. Required: {', '.join(required)}", "warning")
                    return redirect(url_for("admin.batch_upload"))

            preview_data = []
            year = CURRENT_YEAR()

            for idx, row in enumerate(csv_data, 1):
                preview_row = {"row": idx, "errors": []}

                # Parse and validate each field
                try:
                    # System
                    system_name = row.get("system_name", "").strip()
                    system = next((s for s in systems if s["system_name"] == system_name), None)
                    if not system:
                        preview_row["errors"].append(f"System '{system_name}' not found")
                    else:
                        preview_row["system_name"] = system_name
                        preview_row["system_id"] = system["system_id"]

                    # Date
                    date_str = row.get("date", "").strip()
                    try:
                        played_on = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d 12:00:00")
                        preview_row["date"] = date_str
                    except ValueError:
                        preview_row["errors"].append(f"Invalid date format: {date_str} (use YYYY-MM-DD)")

                    # Players
                    p1_name = row.get("player_one", "").strip()
                    p2_name = row.get("player_two", "").strip()
                    if p1_name == p2_name:
                        preview_row["errors"].append("Player 1 and Player 2 cannot be the same")
                    preview_row["player_one"] = p1_name
                    preview_row["player_two"] = p2_name

                    # Factions
                    preview_row["p1_faction"] = row.get("p1_faction", "").strip()
                    preview_row["p2_faction"] = row.get("p2_faction", "").strip()

                    # Result
                    result = row.get("result", "").strip()
                    if result not in ["Player 1 Wins", "Player 2 Wins", "Drawn"]:
                        preview_row["errors"].append(f"Invalid result: {result} (must be 'Player 1 Wins', 'Player 2 Wins', or 'Drawn')")
                    preview_row["result"] = result

                    # Location
                    location_name = row.get("location", "").strip()
                    location = next((l for l in locations if l["name"] == location_name), None)
                    if not location:
                        preview_row["errors"].append(f"Location '{location_name}' not found")
                    else:
                        preview_row["location"] = location_name
                        preview_row["location_id"] = location["location_id"]

                    # Points band
                    points_band = row.get("points_band", "").strip()
                    preview_row["points_band"] = points_band

                    # Notes (optional)
                    preview_row["notes"] = row.get("notes", "").strip()

                except Exception as e:
                    preview_row["errors"].append(str(e))

                preview_data.append(preview_row)

            # Store preview data in session for confirmation
            session["batch_upload_preview"] = preview_data
            session["batch_upload_csv_data"] = csv_data
            session.modified = True
            
        except Exception as e:
            flash(f"Error reading CSV: {str(e)}", "danger")
            return redirect(url_for("admin.batch_upload"))

    return render_template(
        "batch_upload.html",
        preview_data=preview_data,
        systems=systems,
        locations=locations
    )


@admin_bp.route("/batch_upload_confirm", methods=["POST"])
@login_required
def batch_upload_confirm():
    """Confirm and insert batch upload results."""
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to perform this action.", "danger")
        return redirect("/")

    try:
        # Get data from session
        csv_data = session.get("batch_upload_csv_data", [])
        if not csv_data:
            flash("No preview data found. Please upload a file again.", "warning")
            return redirect(url_for("admin.batch_upload"))

        with sqlite3.connect("GPTLeague.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            year = CURRENT_YEAR()
            season_row = cursor.execute(
                "SELECT season_id FROM seasons WHERE year = ?", (year,)
            ).fetchone()
            season_id = season_row["season_id"] if season_row else 1

            # Get systems, locations, factions for lookups
            systems = cursor.execute(
                "SELECT system_id, system_name, category FROM systems"
            ).fetchall()
            locations = cursor.execute(
                "SELECT location_id, name FROM locations"
            ).fetchall()

            games_added = 0
            errors = []

            for idx, row in enumerate(csv_data, 1):
                try:
                    # Get system
                    system = next((s for s in systems if s["system_name"] == row["system_name"].strip()), None)
                    if not system:
                        errors.append(f"Row {idx}: System not found")
                        continue

                    # Get players by username or full_name
                    player_one = cursor.execute(
                        "SELECT user_id FROM users WHERE user_name = ? OR full_name = ?",
                        (row["player_one"].strip(), row["player_one"].strip())
                    ).fetchone()
                    player_two = cursor.execute(
                        "SELECT user_id FROM users WHERE user_name = ? OR full_name = ?",
                        (row["player_two"].strip(), row["player_two"].strip())
                    ).fetchone()

                    if not player_one or not player_two:
                        errors.append(f"Row {idx}: Player not found")
                        continue

                    # Get factions
                    p1_faction = cursor.execute(
                        "SELECT faction_id FROM factions WHERE faction_name = ? AND system_id = ?",
                        (row["p1_faction"].strip(), system["system_id"])
                    ).fetchone()
                    p2_faction = cursor.execute(
                        "SELECT faction_id FROM factions WHERE faction_name = ? AND system_id = ?",
                        (row["p2_faction"].strip(), system["system_id"])
                    ).fetchone()

                    if not p1_faction or not p2_faction:
                        errors.append(f"Row {idx}: Faction not found")
                        continue

                    # Get location
                    location = next((l for l in locations if l["name"] == row["location"].strip()), None)
                    if not location:
                        errors.append(f"Row {idx}: Location not found")
                        continue

                    # Parse date
                    played_on = datetime.strptime(row["date"].strip(), "%Y-%m-%d").strftime("%Y-%m-%d 12:00:00")

                    # Create game entry
                    conn.execute("BEGIN")
                    cursor.execute(
                        "INSERT INTO games (season_id, system_id, played_on, location_id, points_band, notes) VALUES (?,?,?,?,?,?)",
                        (season_id, system["system_id"], played_on, location["location_id"], 
                         row["points_band"].strip(), row.get("notes", "").strip())
                    )
                    game_id = cursor.lastrowid

                    # Map result
                    result = row["result"].strip()
                    if result == "Player 1 Wins":
                        p1_result, p2_result = "win", "loss"
                    elif result == "Player 2 Wins":
                        p1_result, p2_result = "loss", "win"
                    else:  # Drawn
                        p1_result, p2_result = "draw", "draw"

                    # Add participants
                    cursor.execute(
                        "INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready) VALUES (?,?,?,?,?)",
                        (game_id, player_one["user_id"], p1_faction["faction_id"], p1_result, 0)
                    )
                    cursor.execute(
                        "INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready) VALUES (?,?,?,?,?)",
                        (game_id, player_two["user_id"], p2_faction["faction_id"], p2_result, 0)
                    )

                    # Update ratings
                    update_ratings_for_season(season_id, system["system_id"], system["category"], conn)
                    conn.commit()
                    games_added += 1

                except Exception as e:
                    conn.rollback()
                    errors.append(f"Row {idx}: {str(e)}")
                    continue

            # Clear session data
            session.pop("batch_upload_preview", None)
            session.pop("batch_upload_csv_data", None)
            session.modified = True

            flash(f"✅ Successfully added {games_added} games", "success")
            if errors:
                error_msg = "; ".join(errors[:5])  # Show first 5 errors
                if len(errors) > 5:
                    error_msg += f"; ... and {len(errors) - 5} more"
                flash(f"⚠️ Some rows had errors: {error_msg}", "warning")

    except Exception as e:
        flash(f"Error processing batch upload: {str(e)}", "danger")

    return redirect(url_for("admin.batch_upload"))


def generate_temp_password(length=12):
    """Generate a temporary password with uppercase, lowercase, numbers, and symbols."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))


@admin_bp.route("/batch_upload_users", methods=["GET", "POST"])
@login_required
def batch_upload_users():
    """Batch upload users from CSV."""
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    preview_data = None

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected", "warning")
            return redirect(url_for("admin.batch_upload_users"))

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "warning")
            return redirect(url_for("admin.batch_upload_users"))

        if not file.filename.endswith(".csv"):
            flash("Please upload a CSV file", "warning")
            return redirect(url_for("admin.batch_upload_users"))

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
            csv_data = list(csv.DictReader(stream))
            
            if not csv_data:
                flash("CSV file is empty", "warning")
                return redirect(url_for("admin.batch_upload_users"))

            # Required columns
            if csv_data and csv_data[0]:
                required = {"username", "email", "full_name"}
                if not required.issubset(set(csv_data[0].keys())):
                    flash(f"CSV missing required columns. Required: {', '.join(required)}", "warning")
                    return redirect(url_for("admin.batch_upload_users"))

            # Get existing usernames and emails
            with sqlite3.connect("GPTLeague.db") as conn:
                cursor = conn.cursor()
                existing_usernames = set(
                    row[0] for row in cursor.execute("SELECT user_name FROM users").fetchall()
                )
                existing_emails = set(
                    row[0] for row in cursor.execute("SELECT email FROM users").fetchall()
                )

            preview_data = []
            for idx, row in enumerate(csv_data, 1):
                preview_row = {"row": idx, "errors": []}

                # Validate username
                username = row.get("username", "").strip()
                if not username:
                    preview_row["errors"].append("Username is required")
                elif len(username) < 3:
                    preview_row["errors"].append("Username must be at least 3 characters")
                elif not all(c.isalnum() or c == '_' for c in username):
                    preview_row["errors"].append("Username can only contain letters, numbers, and underscores")
                elif username in existing_usernames:
                    preview_row["errors"].append(f"Username '{username}' already exists")
                else:
                    preview_row["username"] = username

                # Validate email
                email = row.get("email", "").strip()
                if not email:
                    preview_row["errors"].append("Email is required")
                elif not is_valid_email(email):
                    preview_row["errors"].append("Invalid email format")
                elif email in existing_emails:
                    preview_row["errors"].append(f"Email '{email}' already exists")
                else:
                    preview_row["email"] = email

                # Validate full name
                full_name = row.get("full_name", "").strip()
                if not full_name:
                    preview_row["errors"].append("Full name is required")
                elif len(full_name) < 2:
                    preview_row["errors"].append("Full name must be at least 2 characters")
                else:
                    preview_row["full_name"] = full_name

                preview_data.append(preview_row)

            # Store preview data in session for confirmation
            session["batch_upload_users_preview"] = preview_data
            session["batch_upload_users_csv_data"] = csv_data
            session.modified = True
            
        except Exception as e:
            flash(f"Error reading CSV: {str(e)}", "danger")
            return redirect(url_for("admin.batch_upload_users"))

    return render_template("batch_upload_users.html", preview_data=preview_data)


@admin_bp.route("/batch_upload_users_confirm", methods=["POST"])
@login_required
def batch_upload_users_confirm():
    """Confirm and insert batch uploaded users."""
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to perform this action.", "danger")
        return redirect("/")

    try:
        # Get data from session
        csv_data = session.get("batch_upload_users_csv_data", [])
        preview_data = session.get("batch_upload_users_preview", [])
        
        if not csv_data or not preview_data:
            flash("No preview data found. Please upload a file again.", "warning")
            return redirect(url_for("admin.batch_upload_users"))

        with sqlite3.connect("GPTLeague.db") as conn:
            cursor = conn.cursor()

            # Get current season
            year = CURRENT_YEAR()
            season_row = cursor.execute(
                "SELECT season_id FROM seasons WHERE year = ?", (year,)
            ).fetchone()
            season_id = season_row[0] if season_row else 1

            users_added = 0
            temp_passwords = []

            for idx, (preview_row, csv_row) in enumerate(zip(preview_data, csv_data)):
                if preview_row.get("errors"):
                    continue  # Skip rows with errors

                try:
                    username = preview_row.get("username")
                    email = preview_row.get("email")
                    full_name = preview_row.get("full_name")
                    
                    # Generate temporary password
                    temp_password = generate_temp_password()
                    password_hash = hash_password(temp_password)
                    
                    # Insert user
                    cursor.execute(
                        "INSERT INTO users (user_name, email, full_name, password_hash, is_active) VALUES (?,?,?,?,?)",
                        (username, email, full_name, password_hash, 1)
                    )
                    new_user_id = cursor.lastrowid
                    
                    # Add as player role
                    cursor.execute(
                        "INSERT INTO user_roles (user_id, role) VALUES (?,?)",
                        (new_user_id, 'player')
                    )
                    
                    # Auto-enroll in current season
                    cursor.execute(
                        "INSERT INTO club_memberships (season_id, user_id, is_member) VALUES (?,?,?)",
                        (season_id, new_user_id, 1)
                    )
                    
                    # Store temp password for display
                    temp_passwords.append({
                        "username": username,
                        "email": email,
                        "full_name": full_name,
                        "temp_password": temp_password
                    })
                    
                    users_added += 1

                except Exception as e:
                    flash(f"Row {idx + 1}: {str(e)}", "warning")
                    conn.rollback()
                    continue

            conn.commit()

            # Clear session data
            session.pop("batch_upload_users_preview", None)
            session.pop("batch_upload_users_csv_data", None)
            session.modified = True

            if users_added > 0:
                flash(f"✅ Successfully added {users_added} user(s)", "success")
                # Store temp passwords in session to display
                session["batch_upload_temp_passwords"] = temp_passwords
                session.modified = True
                return redirect(url_for("admin.batch_upload_users_complete"))
            else:
                flash("No valid users to add", "warning")
                return redirect(url_for("admin.batch_upload_users"))

    except Exception as e:
        flash(f"Error processing batch upload: {str(e)}", "danger")
        return redirect(url_for("admin.batch_upload_users"))


@admin_bp.route("/batch_upload_users_complete")
@login_required
def batch_upload_users_complete():
    """Display temporary passwords for newly created users."""
    user_id = session["user_id"]
    if not is_admin(user_id):
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    temp_passwords = session.pop("batch_upload_temp_passwords", [])
    
    if not temp_passwords:
        flash("No temp passwords to display", "warning")
        return redirect(url_for("admin.batch_upload_users"))

    return render_template("batch_upload_users_complete.html", users=temp_passwords)
