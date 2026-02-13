"""Admin and membership management routes."""
import sqlite3
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from helpers import is_admin, login_required, CURRENT_YEAR

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
            SELECT u.user_id, u.user_name,
                COALESCE(cm.is_member, 0) AS is_member
            FROM users u
            LEFT JOIN club_memberships cm
            ON cm.user_id = u.user_id AND cm.season_id = ?
            ORDER BY u.user_name
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
            SELECT p.player_id, p.player_name,
                   COALESCE(sm.is_active, 0) AS is_active
            FROM players p
            LEFT JOIN system_memberships sm
            ON sm.player_id = p.player_id AND sm.system_id = ?
            ORDER BY p.player_name
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
                INSERT INTO system_memberships (player_id, system_id, is_active, joined_on)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(player_id, system_id) DO UPDATE SET is_active = excluded.is_active
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
            SELECT u.user_id, u.user_name,
                   COALESCE(cm.is_member, 0) AS is_member
            FROM users u
            LEFT JOIN club_memberships cm
            ON cm.user_id = u.user_id AND cm.season_id = ?
            ORDER BY u.user_name
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
            SELECT u.user_id, u.user_name,
                   COALESCE(sm.is_active, 0) AS is_active
            FROM users u
            LEFT JOIN system_memberships sm
            ON sm.player_id = u.user_id AND sm.system_id = ?
            ORDER BY u.user_name
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
