"""Statistics routes: faction stats, player stats, store reports."""
import sqlite3
import json
import plotly
import plotly.graph_objs as go
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from helpers import apology, login_required, CURRENT_YEAR, season, all_seasons

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
                print(system, graphs[system])
            
            years_seasons = all_seasons()

            return render_template(
                "factionstats.html",
                 factions=factions, 
                 graphs=graphs, 
                 years=years_seasons, 
                 selected_year=selected_year
                )
    except Exception as e:
        print(f"Error: {e}")
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
                         
            years_seasons = all_seasons()

            return render_template(
                "playerstats.html",
                factions=factions,
                users=users_results,
                active=active,
                graphs=graphs,
                years=years_seasons,
                selected_year=selected_year
            )
        
    except Exception as e:
        print(f"Error: {e}")
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

            # Handle system selection
            selected_system_id = request.args.get("system", "1")

            # Date range
            if selected_year != 'All':
                start_date, end_date = season(selected_year)
            else:
                start_date = '0000-01-01'
                end_date = cursor.execute("SELECT DATE('now')").fetchone()[0]

            # Query: count games per store
            if selected_year == 'All':
                store_counts = cursor.execute("""
                    SELECT l.name AS store_name, COUNT(g.game_id) AS games_played
                    FROM games g
                    JOIN locations l ON g.location_id = l.location_id
                    WHERE g.played_on BETWEEN ? AND ?
                    AND g.system_id = ?
                    GROUP BY l.name
                    ORDER BY games_played DESC;
                """, (start_date, end_date, selected_system_id)).fetchall()
            else:
                store_counts = cursor.execute("""
                    SELECT l.name AS store_name, COUNT(g.game_id) AS games_played
                    FROM games g
                    JOIN locations l ON g.location_id = l.location_id
                    JOIN seasons s ON g.season_id = s.season_id
                    WHERE g.played_on BETWEEN ? AND ?
                    AND g.system_id = ?
                    AND s.year = ?
                    GROUP BY l.name
                    ORDER BY games_played DESC;
                """, (start_date, end_date, selected_system_id, selected_year)).fetchall()

            labels = [row["store_name"] for row in store_counts]
            values = [row["games_played"] for row in store_counts]

            years_seasons = cursor.execute("""
                SELECT year 
                FROM seasons 
                WHERE status IN ('archived', 'active')
                ORDER BY year DESC
            """).fetchall()

            systems_list = cursor.execute("SELECT system_id, system_name FROM systems ORDER BY system_name").fetchall()

            return render_template(
                "store_reports.html",
                labels=labels,
                values=values,
                store_counts=store_counts,
                years=years_seasons,
                selected_year=selected_year,
                CURRENT_YEAR=year,
                systems=systems_list,
                selected_system=selected_system_id
            )

    except Exception as e:
        print(f"Error: {e}")
        flash("An error occurred loading store reports", "warning")
        return redirect("/")
