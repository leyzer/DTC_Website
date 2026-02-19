"""Leagues and game management routes."""
import sqlite3
import logging
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from helpers import apology, is_admin, login_required, CURRENT_YEAR, season
from ratings import update_ratings_for_season

logger = logging.getLogger(__name__)

leagues_bp = Blueprint('leagues', __name__)


@leagues_bp.route("/league", methods=["GET", "POST"])
@login_required
def league():
    user_id = session["user_id"]

    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            # Load base data
            users = cursor.execute(
                "SELECT user_id AS id, user_name, full_name FROM users ORDER BY user_name"
            ).fetchall()

            systems = cursor.execute(
                "SELECT system_id, system_name, category FROM systems ORDER BY system_name"
            ).fetchall()

            # Ensure selected_system_id is defined
            selected_system_id = request.args.get("system", "1")
            selected_system = next(
                (s for s in systems if str(s["system_id"]) == selected_system_id),
                systems[0]
            )
            system_category = selected_system["category"]

            factions = cursor.execute(
                "SELECT faction_id AS id, faction_name FROM factions WHERE system_id = ? ORDER BY faction_name",
                (selected_system_id,)
            ).fetchall()

            locations = cursor.execute(
                "SELECT location_id, name, location_type, city FROM locations ORDER BY name"
            ).fetchall()

            points_bands = cursor.execute(
                "SELECT DISTINCT points_band FROM elo_rules WHERE category = ? ORDER BY points_band",
                (system_category,)
            ).fetchall()

            if request.method == "POST":
                raw_date = request.form.get("date")
                played_on = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M")
                played_on_str = played_on.strftime("%Y-%m-%d %H:%M:%S")

                location = request.form.get("location")
                points_band = request.form.get("points_band")
                notes = request.form.get("notes")
                system_id = request.form.get("system")
                player_one = request.form.get("player_one")
                p1_faction = request.form.get("p1_faction")
                p1_battle_ready = 1 if request.form.get("p1_battle_ready") else 0

                player_two = request.form.get("player_two")
                p2_faction = request.form.get("p2_faction")
                p2_battle_ready = 1 if request.form.get("p2_battle_ready") else 0

                result = request.form.get("result")

                # Validation
                if not all([player_one, player_two, p1_faction, p2_faction, location, points_band, system_id]):
                    flash('Please confirm all required fields', 'warning')
                    return redirect(f"/league?system={system_id}")

                if player_one == player_two:
                    flash('Both players cannot be the same', 'warning')
                    return redirect(f"/league?system={system_id}")

                if result is None:
                    flash('Please choose result', 'warning')
                    return redirect(f"/league?system={system_id}")

                system_category = cursor.execute(
                    "SELECT category FROM systems WHERE system_id = ?",
                    (system_id,)
                ).fetchone()["category"]

                # Season lookup
                year = CURRENT_YEAR()
                season_row = cursor.execute(
                    "SELECT season_id FROM seasons WHERE year = ?",
                    (year,)
                ).fetchone()
                season_id = season_row["season_id"] if season_row else 1
                
                # Check if user has admin role
                admin_check = cursor.execute(
                    "SELECT 1 FROM user_roles WHERE user_id = ? AND role = 'admin'",
                    (user_id,)
                ).fetchone()

                if not admin_check:
                    flash("You do not have permission to input results", "danger")
                    return redirect("/league")

                try:
                    connection.execute("BEGIN")

                    cursor.execute(
                        "INSERT INTO games (season_id, system_id, played_on, location_id, points_band, notes) VALUES (?,?,?,?,?,?)",
                        (season_id, system_id, played_on_str, location, points_band, notes)
                    )
                    game_id = cursor.lastrowid
                    logger.debug(f"Game created with ID {game_id}")

                    # Result mapping
                    if result == "Player 1 Wins":
                        p1_result, p2_result = 'win', 'loss'
                    elif result == "Player 2 Wins":
                        p1_result, p2_result = 'loss', 'win'
                    elif result == "Drawn":
                        p1_result = p2_result = 'draw'

                    # Player 1
                    cursor.execute(
                        "INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready) VALUES (?,?,?,?,?)",
                        (game_id, player_one, p1_faction, p1_result, p1_battle_ready)
                    )
                    logger.debug(f"Player 1 ({player_one}) inserted into game {game_id}")

                    # Player 2
                    cursor.execute(
                        "INSERT INTO game_participants (game_id, player_id, faction_id, result, painting_battle_ready) VALUES (?,?,?,?,?)",
                        (game_id, player_two, p2_faction, p2_result, p2_battle_ready)
                    )
                    logger.debug(f"Player 2 ({player_two}) inserted into game {game_id}")

                    # Update ratings
                    update_ratings_for_season(season_id, system_id, system_category, connection)
                    connection.commit()
                except Exception as e:
                    connection.rollback()
                    raise

                flash("Game result recorded successfully!", "success")
                return redirect(f"/league?system={system_id}")
            else:
                current_user = cursor.execute(
                    "SELECT user_id, user_name FROM users WHERE user_id=?",
                    (user_id,)
                ).fetchone()
            today = datetime.now().strftime("%Y-%m-%dT%H:%M")

            return render_template(
                "league.html",
                users=users,
                factions=factions,
                locations=locations,
                points_bands=points_bands,
                systems=systems,
                selected_system_id=selected_system_id,
                system_name=selected_system["system_name"],
                today=today
            )

    except Exception as e:
        logger.error(f"Error in league: {str(e)}")
        flash('An error occurred loading league', 'warning')
        return redirect("/league")


@leagues_bp.route("/gamesPlayed/<int:system_id>", methods=["GET", "POST"])
@login_required
def gamesPlayed(system_id):
    from helpers import all_seasons
    
    user_id = session["user_id"]
    year = CURRENT_YEAR()

    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            # Check admin role
            admin_row = cursor.execute(
                "SELECT 1 FROM user_roles WHERE user_id = ? AND role = 'admin'",
                (user_id,)
            ).fetchone()
            admin = bool(admin_row)

            # Handle year selection
            if request.method == "POST":
                selected_year = request.form.get("year")
                if selected_year and selected_year != 'All':
                    selected_year = int(selected_year)
                else:
                    selected_year = year
            else:
                selected_year = year

            sys_row = cursor.execute(
                "SELECT system_name FROM systems WHERE system_id = ?",
                (system_id,)
            ).fetchone()
            if not sys_row:
                flash("Invalid system selected.", "warning")
                return redirect(url_for("leagues.gamesPlayed", system_id=1))
            system_name = sys_row["system_name"]

            # Date range
            if selected_year != 'All':
                start_date, end_date = season(selected_year)
            else:
                start_date = '0000-01-01'
                end_date = cursor.execute("SELECT DATE('now')").fetchone()[0]

            # Query games
            gameslist_result = cursor.execute("""
                SELECT g.game_id, g.played_on, g.score, g.ignored,
                    gp1.player_id, u1.full_name,
                    gp2.player_id, u2.full_name,
                    l.name                          
                FROM games g
                JOIN game_participants gp1 ON g.game_id = gp1.game_id
                JOIN game_participants gp2 ON g.game_id = gp2.game_id
                JOIN users u1 ON gp1.player_id = u1.user_id
                JOIN users u2 ON gp2.player_id = u2.user_id
                JOIN seasons s ON g.season_id = s.season_id
                LEFT JOIN locations l ON g.location_id = l.location_id
                LEFT JOIN club_memberships cm1 ON cm1.user_id = gp1.player_id
                    AND cm1.season_id = s.season_id
                LEFT JOIN club_memberships cm2 ON cm2.user_id = gp2.player_id
                    AND cm2.season_id = s.season_id
                WHERE gp1.player_id < gp2.player_id
                AND g.played_on BETWEEN ? AND ?
                AND s.year = ?
                AND g.system_id = ?
                ORDER BY g.played_on DESC;
            """, (start_date, end_date, selected_year, system_id)).fetchall()

            # Build dictionary
            game_dict = {
                game_id: {
                    "player1_id": p1_id,
                    "player1_name": p1_name,                    
                    "p1_gen": 0,
                    "player2_id": p2_id,
                    "player2_name": p2_name,                    
                    "p2_gen": 0,
                    "date": datetime.strptime(date, "%Y-%m-%d %H:%M:%S"),  
                    "score": score,
                    "winnerID": None,
                    "ignored": ignored,
                    "location": location
                }
                for game_id, date, score, ignored,
                    p1_id, p1_name, 
                    p2_id, p2_name,
                    location in gameslist_result
            }

            # Enrich with ratings for this system - batch all queries
            # Extract unique player and game IDs
            all_player_ids = set()
            for data in game_dict.values():
                all_player_ids.add(data["player1_id"])
                all_player_ids.add(data["player2_id"])

            all_game_ids = list(game_dict.keys())
            player_ids_list = list(all_player_ids)

            # Build placeholders for IN clauses
            player_placeholders = ','.join('?' * len(player_ids_list))
            game_placeholders = ','.join('?' * len(all_game_ids))

            # Fetch all club memberships in one query
            club_memberships = cursor.execute(f"""
                SELECT user_id
                FROM club_memberships
                JOIN seasons ON club_memberships.season_id = seasons.season_id
                WHERE seasons.year = ? AND is_member = 1 AND user_id IN ({player_placeholders})
            """, [selected_year] + player_ids_list).fetchall()
            club_set = {row[0] for row in club_memberships}

            # Fetch all current ratings in one query
            all_ratings = cursor.execute(f"""
                SELECT player_id, current_rating
                FROM ratings
                JOIN seasons ON seasons.season_id = ratings.season_id
                WHERE seasons.year = ? AND ratings.system_id = ? AND player_id IN ({player_placeholders})
            """, [selected_year, system_id] + player_ids_list).fetchall()
            ratings_lookup = {row[0]: row[1] for row in all_ratings}

            # Fetch all rating history in one query
            all_history = cursor.execute(f"""
                SELECT game_id, player_id, old_rating, new_rating
                FROM rating_history
                WHERE system_id = ? AND game_id IN ({game_placeholders})
            """, [system_id] + all_game_ids).fetchall()
            history_lookup = {(row[0], row[1]): (row[2], row[3]) for row in all_history}

            # Fetch all winners in one query
            all_winners = cursor.execute(f"""
                SELECT game_id, player_id
                FROM game_participants
                WHERE game_id IN ({game_placeholders}) AND result = 'win'
            """, all_game_ids).fetchall()
            winners_lookup = {row[0]: row[1] for row in all_winners}

            # Enrich game_dict with pre-fetched data
            for game_id, data in game_dict.items():
                p1_id, p2_id = data["player1_id"], data["player2_id"]

                # Set club membership from pre-fetched data
                data["player1_club_member"] = p1_id in club_set
                data["player2_club_member"] = p2_id in club_set

                # Set current ratings from pre-fetched data
                data["p1_gen"] = ratings_lookup.get(p1_id, 0)
                data["p2_gen"] = ratings_lookup.get(p2_id, 0)

                # Override with rating history if available (more recent)
                if (game_id, p1_id) in history_lookup:
                    old, new = history_lookup[(game_id, p1_id)]
                    data["p1_gen"] = round(new, 2)
                    data["p1_change"] = round(new - old, 2)

                if (game_id, p2_id) in history_lookup:
                    old, new = history_lookup[(game_id, p2_id)]
                    data["p2_gen"] = round(new, 2)
                    data["p2_change"] = round(new - old, 2)

                # Set winner from pre-fetched data
                data["winnerID"] = winners_lookup.get(game_id)

            years_seasons = all_seasons()
            systems_list = cursor.execute("SELECT system_id, system_name FROM systems").fetchall()

            return render_template(
                "gamesPlayed.html",
                game_dict=game_dict,
                admin=admin,
                years=years_seasons,
                selected_year=selected_year,
                CURRENT_YEAR=year,
                systems=systems_list,
                selected_system=system_id,
                system_id=system_id,
                system_name=system_name
            )

    except Exception as e:
        logger.exception("Error in gamesPlayed")
        flash('An error occurred loading Games Played listing', 'warning')
        return apology("An error occurred loading Games Played listing", 400)


@leagues_bp.route("/recalculate_ratings", methods=["POST"])
@login_required
def recalc_ratings():
    from ratings import process_ratings
    
    user_id = session["user_id"]

    # Check if user is admin
    with sqlite3.connect("GPTLeague.db") as conn:
        cursor = conn.cursor()
        admin_row = cursor.execute(
            "SELECT 1 FROM user_roles WHERE user_id = ? AND role = 'admin'",
            (user_id,)
        ).fetchone()

    system_id = request.form.get("system_id")
    season_id = request.form.get("season_id")

    if not admin_row:
        flash("You do not have permission to recalculate ratings.", "danger")
        return redirect(url_for("leagues.gamesPlayed", system_id=system_id))

    if not season_id or not system_id:
        flash("Season and system must be selected for recalculation.", "warning")
        return redirect(url_for("leagues.gamesPlayed", system_id=system_id))

    try:
        season_id = int(season_id)
        system_id = int(system_id)

        process_ratings(season_id, system_id)

        with sqlite3.connect("GPTLeague.db") as conn:
            cursor = conn.cursor()
            sys_row = cursor.execute(
                "SELECT system_name FROM systems WHERE system_id = ?",
                (system_id,)
            ).fetchone()
            system_name = sys_row[0] if sys_row else f"System {system_id}"

        flash(f"Ratings recalculated successfully for season {season_id}, {system_name}!", "success")
    except Exception as e:
        flash(f"Error recalculating ratings: {e}", "danger")

    return redirect(url_for("leagues.gamesPlayed", system_id=system_id))


@leagues_bp.route("/toggleIgnored", methods=["POST"])
@login_required
def toggleIgnored():
    if not is_admin(session["user_id"]):
        flash("Not authorized", "danger")
        return redirect("/gamesPlayed")

    game_id = request.form.get("game_id")
    ignored = 1 if request.form.get("ignored") else 0

    with sqlite3.connect('GPTLeague.db') as connection:
        cursor = connection.cursor()
        cursor.execute("UPDATE games SET ignored = ? WHERE game_id = ?", (ignored, game_id))
        connection.commit()

    flash("Game updated", "success")
    return redirect("/gamesPlayed")
