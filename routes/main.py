"""Main and core routes: home page, about, profile."""
import sqlite3
import logging
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, send_file
from helpers import apology, login_required, hash_password, CURRENT_YEAR, all_seasons

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route("/", methods=["GET", "POST"])
def home():
    """Redirect home to the Overall league standings page."""
    return redirect(url_for('stats.overall'))


@main_bp.route("/elo_ratings", methods=["GET", "POST"])
def elo_ratings():
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            # Get latest year from seasons
            latest_year_row = cursor.execute("SELECT MAX(year) AS latest_year FROM seasons").fetchone()
            latest_year = latest_year_row["latest_year"] if latest_year_row else CURRENT_YEAR()

            # Handle year selection
            if request.method == "POST":
                selected_year = request.form.get("year")
                if selected_year and selected_year.isnumeric():
                    selected_year = int(selected_year)
            else:
                selected_year = latest_year

            # Get current user stats if logged in
            user_stats = None
            if 'user_id' in session:
                user_id = session["user_id"]
                user_stats = cursor.execute("""
                    SELECT 
                        u.full_name,
                        u.user_name,
                        COUNT(DISTINCT g.game_id) as total_games,
                        SUM(CASE WHEN gp.result = 'win' THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN gp.result = 'loss' THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN gp.result = 'draw' THEN 1 ELSE 0 END) as draws,
                        AVG(r.current_rating) as avg_rating,
                        COUNT(DISTINCT f.system_id) as systems_played
                    FROM users u
                    LEFT JOIN game_participants gp ON u.user_id = gp.player_id
                    LEFT JOIN games g ON gp.game_id = g.game_id
                    LEFT JOIN ratings r ON u.user_id = r.player_id
                    LEFT JOIN factions f ON gp.faction_id = f.faction_id
                    WHERE u.user_id = ? AND g.season_id = (SELECT season_id FROM seasons WHERE year = ?)
                    GROUP BY u.user_id
                """, (user_id, selected_year)).fetchone()

            # Get all systems
            systems_list = cursor.execute("""
                SELECT system_id, system_code, system_name
                FROM systems
                ORDER BY system_name
            """).fetchall()

            # Build dictionary: {system_code: [users]}
            system_tables = {}
            for sys in systems_list:
                rows = cursor.execute("""
                    SELECT 
                        u.user_id AS id,
                        u.full_name,
                        r.current_rating AS rating,
                        s.year,
                        s.name AS season_name,
                        COALESCE(sm.is_active, 0) AS system_member,
                        COALESCE(cm.is_member, 0) AS club_member
                    FROM users u
                    JOIN ratings r ON u.user_id = r.player_id
                    JOIN seasons s ON r.season_id = s.season_id
                    LEFT JOIN system_memberships sm 
                        ON sm.user_id = r.player_id AND sm.system_id = r.system_id
                    LEFT JOIN club_memberships cm 
                        ON cm.user_id = u.user_id AND cm.season_id = s.season_id
                    WHERE s.year = ? AND r.system_id = ? AND sm.is_active = 1
                    ORDER BY r.current_rating DESC
                """, (selected_year, sys["system_id"])).fetchall()

                users = [dict(row) for row in rows]
                for user in users:
                    user["rating"] = round(user["rating"]) if user["rating"] else 400
                    user["system_member"] = bool(user["system_member"])
                    user["club_member"] = bool(user["club_member"])

                system_tables[sys["system_code"]] = {
                    "system_name": sys["system_name"],
                    "users": users
                }

            # Sort by system code
            system_tables_sorted = dict(
                sorted(system_tables.items(), key=lambda item: item[0])
            )

            years_seasons = all_seasons()
            return render_template(
                "elo_ratings.html",
                system_tables=system_tables_sorted,
                years=years_seasons,
                selected_year=selected_year,
                user_stats=user_stats
            )

    except Exception as e:
        logger.error(f"Error in elo_ratings: {str(e)}")
        return apology("An error occurred", 400)


@main_bp.route("/about", methods=["GET"])
def about():
    return render_template("about.html")


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = int(session["user_id"])
    year = CURRENT_YEAR()
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            
            if request.method == "GET":  
                # Get current user info
                user = cursor.execute(
                    "SELECT user_id, email, user_name, full_name, is_active, created_at FROM users WHERE user_id=?", 
                    (user_id,)
                ).fetchone()
                
                # Check if user is admin
                from helpers import is_admin
                is_user_admin = is_admin(user_id)
                
                # Get all users for admin dropdown (if user is admin)
                users_list = []
                if is_user_admin:
                    users_list = cursor.execute("""
                        SELECT u.user_id, u.user_name, u.full_name,
                        CASE WHEN EXISTS (
                            SELECT 1 FROM user_roles 
                            WHERE user_roles.user_id = u.user_id AND role = 'admin'
                        ) THEN 1 ELSE 0 END AS is_admin 
                        FROM users u
                        ORDER BY u.user_name
                    """).fetchall()
                
                return render_template("profile.html", 
                                       user=user, 
                                       users_list=users_list, 
                                       is_user_admin=is_user_admin,
                                       CURRENT_YEAR=year)
            else:
                from helpers import is_admin
                if not is_admin(user_id):
                    flash("You do not have permission to modify user roles.", "danger")
                    return redirect("/profile")
                
                userID = int(request.form.get("admin"))
                if userID != user_id:
                    user = cursor.execute("SELECT user_id FROM users WHERE user_id=?", (userID,)).fetchone()  
                    
                    if user:
                        # Check if user already has admin role
                        admin_check = cursor.execute(
                            "SELECT 1 FROM user_roles WHERE user_id = ? AND role = 'admin'",
                            (userID,)
                        ).fetchone()
                        
                        if admin_check:
                            cursor.execute("DELETE FROM user_roles WHERE user_id = ? AND role = 'admin'", (userID,))
                            flash('Admin rights removed', 'warning')
                        else:
                            cursor.execute("INSERT INTO user_roles (user_id, role) VALUES (?, 'admin')", (userID,))
                            flash('Admin rights applied', 'success')
                        connection.commit()
                
                return redirect("/profile")        

    except Exception as e:
        logger.error(f"Error in profile: {str(e)}")
        flash('An error occurred loading profile', 'warning')
        return apology("An error occurred loading profile", 400)


@main_bp.route("/league_formats")
def league_formats():
    """Display league format options (Option A vs Option B)."""
    return render_template("leagueFormats.html")


@main_bp.route("/documents")
def documents():
    """Display club documents, policies, and rules."""
    return render_template("documents.html")


@main_bp.route("/events")
def events():
    """Display club events calendar."""
    return render_template("events.html")


@main_bp.route("/people")
def people():
    """Display club people - committee, praetors, tribunes, and partner stores."""
    return render_template("people.html")


@main_bp.route("/contact")
def contact():
    """Display contact us page with Google Form."""
    return render_template("contact.html")


@main_bp.route("/sample_batch_upload.csv")
def download_sample_csv():
    """Download sample CSV file for batch upload."""
    import os
    sample_file = os.path.join(os.path.dirname(__file__), '..', 'sample_batch_upload.csv')
    return send_file(
        sample_file,
        as_attachment=True,
        download_name="sample_batch_upload.csv",
        mimetype="text/csv"
    )
