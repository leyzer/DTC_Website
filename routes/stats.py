"""Statistics routes: faction stats, player stats, store reports."""
import logging
import sqlite3
import json
import plotly
import plotly.graph_objs as go
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from helpers import apology, login_required, CURRENT_YEAR, season, all_seasons

logger = logging.getLogger(__name__)
stats_bp = Blueprint('stats', __name__)


@stats_bp.route("/factionstats", methods=["GET", "POST"])
def factionstats():
    selected_year = CURRENT_YEAR()
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            if request.method == "POST":
                selected_year = request.form.get("year")
                if selected_year != 'All':
                    selected_year = int(selected_year)

            if selected_year != 'All':
                start_date, end_date = season(selected_year)                
            else:
                start_date = '0000-01-01'
                end_date = cursor.execute("SELECT DATE('now')").fetchone()[0]      
          
            factions_stats = cursor.execute("""
                                            SELECT 
                                                CASE 
                                                WHEN gp.result = 'win' THEN 1  
                                                WHEN gp.result = 'loss' THEN 0 
                                                WHEN gp.result = 'draw' THEN 2 
                                            END AS win, 
                                            gp.faction_id AS faction, 
                                            f.faction_id AS id, 
                                            f.faction_name, 
                                            s.system_name, 
                                            gp.painting_battle_ready AS painted 
                                            FROM game_participants gp 
                                            JOIN factions f ON f.faction_id = gp.faction_id
                                            JOIN games g ON g.game_id = gp.game_id 
                                            JOIN systems s ON s.system_id = f.system_id
                                            WHERE g.played_on >= ? AND g.played_on <= ? 
                                            ORDER BY s.system_name, f.faction_name
                                        """, (start_date, end_date)).fetchall()
            
            factions = {}    
            if factions_stats:
                for row in factions_stats:
                    system = row["system_name"]
                    faction = row["faction_name"]

                    if system not in factions:
                        factions[system] = {}

                    if faction not in factions[system]:
                        factions[system][faction] = {
                            "games": 0, "wins": 0, "losses": 0, "draws": 0, "battle_ready": 0
                        }

                    factions[system][faction]["games"] += 1
                    if row["painted"]:
                        factions[system][faction]["battle_ready"] += 1
                    if row["win"] == 1:
                        factions[system][faction]["wins"] += 1
                    elif row["win"] == 2:
                        factions[system][faction]["draws"] += 1
                    elif row["win"] == 0:
                        factions[system][faction]["losses"] += 1

            graphs = {}
            for system, system_factions in factions.items():
                labels = list(system_factions.keys())
                values = [f["games"] for f in system_factions.values()]
                fig = go.Figure(data=[go.Pie(labels=labels, values=values)])                
                graphs[system] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                logger.debug("Graph generated for system: %s", system)
            
            years_seasons = all_seasons()

            return render_template(
                "factionstats.html",
                 factions=factions, 
                 graphs=graphs, 
                 years=years_seasons, 
                 selected_year=selected_year
                )
    except Exception as e:
        logger.error("An error occurred in stats route")
        flash('An error occurred loading faction stats', 'warning')
        return apology("An error occurred loading faction stats", 400)


@stats_bp.route("/playerstats", methods=["GET", "POST"])
@login_required
def playerstats():
    year = CURRENT_YEAR()
    user_id = session["user_id"]
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            if request.method == "GET":      
                player = user_id
                selected_year = year
            else:                
                player = request.form.get("player", user_id)
                selected_year = request.form.get("year", year)
                if selected_year != 'All':
                    selected_year = int(selected_year)
                                   
            if selected_year != 'All':
                start_date, end_date = season(selected_year)                
            else:
                start_date = '0000-01-01'
                end_date = cursor.execute("SELECT DATE('now')").fetchone()[0]

            users_results = cursor.execute("SELECT user_name,user_id FROM users").fetchall()
            active = cursor.execute("SELECT user_name,user_id FROM users WHERE user_id=?", (player,)).fetchone()
            
            # Get current user info
            current_user_info = cursor.execute("SELECT user_id, user_name FROM users WHERE user_id=?", (user_id,)).fetchone()
            
            my_overall = cursor.execute("""
                SELECT                    
                    u.user_id AS player_id,
                    u.user_name AS user_name,
                    g.system_id,
                    s.system_name,                     
                    CASE 
                        WHEN gp.result = 'win' THEN 1 
                        WHEN gp.result = 'loss' THEN 0 
                        WHEN gp.result = 'draw' THEN 2 
                    END AS result_code,
                    gp.faction_id AS faction,
                    f.faction_name,                                       
                    gp.game_id,
                    gp.painting_battle_ready AS battle_ready
                FROM game_participants gp
                JOIN users u ON u.user_id = gp.player_id
                JOIN factions f ON f.faction_id = gp.faction_id
                JOIN games g ON g.game_id = gp.game_id
                JOIN systems s ON s.system_id = g.system_id
                WHERE gp.player_id = ? AND g.played_on BETWEEN ? AND ?
                ORDER BY s.system_name,f.faction_name
            """, (player, start_date, end_date)).fetchall()
       
            factions = {}
            for row in my_overall:
                system = row["system_name"]
                faction = row["faction_name"]

                if system not in factions:
                    factions[system] = {}

                if faction not in factions[system]:
                    factions[system][faction] = {
                        "games": 0, "wins": 0, "losses": 0, "draws": 0, "battle_ready": 0
                    }

                factions[system][faction]["games"] += 1
                if row["battle_ready"]:
                    factions[system][faction]["battle_ready"] += 1
                if row["result_code"] == 1:
                    factions[system][faction]["wins"] += 1
                elif row["result_code"] == 2:
                    factions[system][faction]["draws"] += 1
                elif row["result_code"] == 0:
                    factions[system][faction]["losses"] += 1                

            graphs = {}
            for system, system_factions in factions.items():
                labels = list(system_factions.keys())
                values = [f["games"] for f in system_factions.values()]
                graph = go.Figure(data=[go.Pie(labels=labels, values=values)])
                graphs[system] = json.dumps(graph, cls=plotly.utils.PlotlyJSONEncoder)
            
            # Fetch player's individual games
            player_games = cursor.execute("""
                SELECT 
                    g.game_id,
                    g.played_on,
                    gp.result,
                    gp.faction_id,
                    f.faction_name,
                    u2.user_name AS opponent_name,
                    l.name AS location,
                    s.system_name
                FROM games g
                JOIN game_participants gp ON g.game_id = gp.game_id
                LEFT JOIN game_participants gp2 ON g.game_id = gp2.game_id AND gp2.player_id != gp.player_id
                LEFT JOIN users u2 ON gp2.player_id = u2.user_id
                LEFT JOIN factions f ON gp.faction_id = f.faction_id
                LEFT JOIN locations l ON g.location_id = l.location_id
                JOIN systems s ON g.system_id = s.system_id
                WHERE gp.player_id = ? AND g.played_on BETWEEN ? AND ?
                ORDER BY g.played_on DESC
            """, (player, start_date, end_date)).fetchall()
                         
            years_seasons = all_seasons()

            return render_template(
                "playerstats.html",
                factions=factions,
                users=users_results,
                active=active,
                graphs=graphs,
                years=years_seasons,
                selected_year=selected_year,
                player_games=player_games
            )
        
    except Exception as e:
        logger.error("An error occurred in stats route")
        flash('An error occurred loading player stats', 'warning')
        return apology("An error occurred loading player stats", 400)


@stats_bp.route("/store_reports", methods=["GET", "POST"])
@login_required
def store_reports():
    user_id = session["user_id"]
    year = CURRENT_YEAR()

    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            # Handle year selection
            if request.method == "POST":
                selected_year = request.form.get("year")
                if selected_year and selected_year != 'All':
                    selected_year = int(selected_year)
                else:
                    selected_year = year
            else:
                selected_year = year

            # Date range
            if selected_year != 'All':
                start_date, end_date = season(selected_year)
            else:
                start_date = '0000-01-01'
                end_date = cursor.execute("SELECT DATE('now')").fetchone()[0]

            # Query: count games per store for ALL systems
            if selected_year == 'All':
                all_systems_stores = cursor.execute("""
                    SELECT 
                        s.system_id,
                        s.system_name,
                        l.name AS store_name, 
                        COUNT(g.game_id) AS games_played
                    FROM games g
                    JOIN locations l ON g.location_id = l.location_id
                    JOIN systems s ON g.system_id = s.system_id
                    WHERE g.played_on BETWEEN ? AND ?
                    GROUP BY s.system_id, s.system_name, l.name
                    ORDER BY s.system_name, games_played DESC;
                """, (start_date, end_date)).fetchall()
            else:
                all_systems_stores = cursor.execute("""
                    SELECT 
                        s.system_id,
                        s.system_name,
                        l.name AS store_name, 
                        COUNT(g.game_id) AS games_played
                    FROM games g
                    JOIN locations l ON g.location_id = l.location_id
                    JOIN seasons se ON g.season_id = se.season_id
                    JOIN systems s ON g.system_id = s.system_id
                    WHERE g.played_on BETWEEN ? AND ?
                    AND se.year = ?
                    GROUP BY s.system_id, s.system_name, l.name
                    ORDER BY s.system_name, games_played DESC;
                """, (start_date, end_date, selected_year)).fetchall()

            # Organize by system
            systems_data = {}
            for row in all_systems_stores:
                system_name = row["system_name"]
                if system_name not in systems_data:
                    systems_data[system_name] = {
                        "system_id": row["system_id"],
                        "stores": []
                    }
                systems_data[system_name]["stores"].append({
                    "store_name": row["store_name"],
                    "games_played": row["games_played"]
                })

            years_seasons = cursor.execute("""
                SELECT year 
                FROM seasons 
                WHERE status IN ('archived', 'active')
                ORDER BY year DESC
            """).fetchall()

            return render_template(
                "store_reports.html",
                systems_data=systems_data,
                years=years_seasons,
                selected_year=selected_year,
                CURRENT_YEAR=year
            )

    except Exception as e:
        logger.error("An error occurred in stats route")
        flash("An error occurred loading store reports", "warning")
        return redirect("/")


@stats_bp.route("/overall", methods=["GET", "POST"])
def overall():
    """Display league results using Option A (points-based) scoring."""
    year = CURRENT_YEAR()
    
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

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

            # Handle year selection
            if request.method == "POST":
                selected_year = request.form.get("year")
                if selected_year and selected_year != 'All':
                    selected_year = int(selected_year)
                else:
                    selected_year = year
            else:
                selected_year = year

            # Date range
            if selected_year != 'All':
                start_date, end_date = season(selected_year)
            else:
                start_date = '0000-01-01'
                end_date = cursor.execute("SELECT DATE('now')").fetchone()[0]

            # Get opponent limit for the selected year
            season_row = cursor.execute("SELECT season_id FROM seasons WHERE year = ?", (selected_year,)).fetchone()
            opponent_limit = 3  # default
            
            if season_row:
                setting_row = cursor.execute("""
                    SELECT setting_value FROM league_settings 
                    WHERE season_id = ? AND setting_key = 'opponent_limit'
                """, (season_row["season_id"],)).fetchone()
                
                if setting_row:
                    opponent_limit = int(setting_row["setting_value"])

            # Get season_id for the selected year
            selected_season = cursor.execute(
                "SELECT season_id FROM seasons WHERE year = ?",
                (selected_year,)
            ).fetchone()
            season_id = selected_season["season_id"] if selected_season else None

            # Fetch all games with details for the selected year (no membership filter)
            if season_id:
                games = cursor.execute("""
                    SELECT 
                        g.game_id,
                        g.played_on,
                        g.points_band,
                        g.system_id,
                        s.system_name,
                        gp1.player_id AS p1_id,
                        u1.user_name AS p1_name,
                        u1.full_name AS p1_full_name,
                        gp1.result AS p1_result,
                        gp2.player_id AS p2_id,
                        u2.user_name AS p2_name,
                        u2.full_name AS p2_full_name,
                        gp2.result AS p2_result
                    FROM games g
                    JOIN game_participants gp1 ON g.game_id = gp1.game_id
                    JOIN game_participants gp2 ON g.game_id = gp2.game_id
                    JOIN users u1 ON gp1.player_id = u1.user_id
                    JOIN users u2 ON gp2.player_id = u2.user_id
                    JOIN systems s ON g.system_id = s.system_id
                    LEFT JOIN seasons se ON g.season_id = se.season_id
                    WHERE g.played_on BETWEEN ? AND ?
                    AND gp1.player_id < gp2.player_id
                    ORDER BY s.system_name, g.played_on
                """, (start_date, end_date)).fetchall()
            else:
                games = []
            
            # Get club members for the season to filter final leaderboard
            club_members = set()
            if season_id:
                member_rows = cursor.execute("""
                    SELECT user_id FROM club_memberships WHERE season_id = ? AND is_member = 1
                """, (season_id,)).fetchall()
                club_members = {row["user_id"] for row in member_rows}

            # Calculate points using Option A scoring with opponent limit
            systems_leaderboards = {}
            
            for game in games:
                system_name = game["system_name"]
                system_id = game["system_id"]
                points_band = game["points_band"]
                
                if system_name not in systems_leaderboards:
                    systems_leaderboards[system_name] = {
                        "system_id": system_id,
                        "players": {}
                    }
                
                # Determine points based on Option A rules
                # Big games (1500+ pts): 4 win, 2 draw, 1 loss
                # Small games (SP/CP/Combat Patrol): 2 win, 1 draw, 0 loss
                if points_band in ['1500', '2000', '1000']:
                    p1_pts = 4 if game["p1_result"] == 'win' else (2 if game["p1_result"] == 'draw' else 1)
                    p2_pts = 4 if game["p2_result"] == 'win' else (2 if game["p2_result"] == 'draw' else 1)
                else:  # SP/CP or other small formats
                    p1_pts = 2 if game["p1_result"] == 'win' else (1 if game["p1_result"] == 'draw' else 0)
                    p2_pts = 2 if game["p2_result"] == 'win' else (1 if game["p2_result"] == 'draw' else 0)
                
                # Add to player records
                players = systems_leaderboards[system_name]["players"]
                
                if game["p1_id"] not in players:
                    players[game["p1_id"]] = {
                        "name": game["p1_name"],
                        "full_name": game["p1_full_name"],
                        "points": 0,
                        "games": 0,
                        "opponent_games": {}
                    }
                
                if game["p2_id"] not in players:
                    players[game["p2_id"]] = {
                        "name": game["p2_name"],
                        "full_name": game["p2_full_name"],
                        "points": 0,
                        "games": 0,
                        "opponent_games": {}
                    }
                
                # Check if we're within the opponent limit for player 1
                if game["p2_id"] not in players[game["p1_id"]]["opponent_games"]:
                    players[game["p1_id"]]["opponent_games"][game["p2_id"]] = 0
                
                if players[game["p1_id"]]["opponent_games"][game["p2_id"]] < opponent_limit:
                    players[game["p1_id"]]["points"] += p1_pts
                    players[game["p1_id"]]["games"] += 1
                    players[game["p1_id"]]["opponent_games"][game["p2_id"]] += 1
                
                # Check if we're within the opponent limit for player 2
                if game["p1_id"] not in players[game["p2_id"]]["opponent_games"]:
                    players[game["p2_id"]]["opponent_games"][game["p1_id"]] = 0
                
                if players[game["p2_id"]]["opponent_games"][game["p1_id"]] < opponent_limit:
                    players[game["p2_id"]]["points"] += p2_pts
                    players[game["p2_id"]]["games"] += 1
                    players[game["p2_id"]]["opponent_games"][game["p1_id"]] += 1
            
            # Sort players by points within each system, only showing club members
            for system_name in systems_leaderboards:
                players_list = list(systems_leaderboards[system_name]["players"].items())
                # Filter to only club members
                players_list = [(pid, pdata) for pid, pdata in players_list if pid in club_members]
                players_list.sort(key=lambda x: x[1]["points"], reverse=True)
                systems_leaderboards[system_name]["ranked"] = players_list
            
            years_seasons = all_seasons()

            return render_template(
                "overall.html",
                systems_leaderboards=systems_leaderboards,
                years=years_seasons,
                selected_year=selected_year,
                opponent_limit=opponent_limit,
                CURRENT_YEAR=year
            )

    except Exception as e:
        logger.error("An error occurred in stats route")
        flash("An error occurred loading Option A results", "warning")
        return redirect("/")

