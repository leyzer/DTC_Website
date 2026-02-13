"""
ratings.py
----------
Handles Elo rating calculations, rating history logging, and ratings table updates
for GPTLeague. Keeps all rating-related logic separate from Flask routes.
"""

import sqlite3
import math


def update_ratings_for_season(season_id, system_id, category, connection, points_band):
    """
    Recalculate Elo ratings for all players in a given season/system/points band.

    Args:
        season_id (int): The season identifier.
        system_id (int): The system identifier (e.g. AoS, 40k).
        category (str): The system category (used for Elo rules).
        connection (sqlite3.Connection): Active database connection.
        points_band (int): Points band for the games (e.g. 1000, 2000).

    Side effects:
        - Updates `ratings` table with current_rating and games_played.
        - Inserts rating changes into `rating_history`.
    """
    cursor = connection.cursor()

    # Get all games for this season/system/category
    games = cursor.execute("""
        SELECT g.game_id, g.played_on, g.points_band,
               gp1.player_id AS p1_id, gp1.result AS p1_result,
               gp2.player_id AS p2_id, gp2.result AS p2_result
        FROM games g
        JOIN game_participants gp1 ON g.game_id = gp1.game_id
        JOIN game_participants gp2 ON g.game_id = gp2.game_id
        JOIN systems s ON g.system_id = s.system_id
        WHERE g.season_id = ? AND g.system_id = ? AND s.category = ? AND gp1.player_id < gp2.player_id
        ORDER BY g.played_on
    """, (season_id, system_id, category)).fetchall()

    # Get K-factor and base rating
    k_factor_row = cursor.execute("""
        SELECT k_factor, base_rating
        FROM elo_rules
        WHERE category = ? AND points_band = ?
        LIMIT 1
    """, (category, points_band)).fetchone()
    if not k_factor_row:
        print(f"No K-factor found for category {category} and points_band {points_band}")
        return
    k_factor, base_rating = k_factor_row

    # Initialize ratings
    current_ratings = {}
    players = cursor.execute("""
        SELECT DISTINCT gp.player_id
        FROM game_participants gp
        JOIN games g ON gp.game_id = g.game_id
        WHERE g.season_id = ? AND g.system_id = ?
    """, (season_id, system_id)).fetchall()
    for player in players:
        current_ratings[player[0]] = base_rating

    # Clear rating history for this season/system
    cursor.execute("""
        DELETE FROM rating_history
        WHERE game_id IN (SELECT game_id FROM games WHERE season_id = ? AND system_id = ?)
    """, (season_id, system_id))

    # Process games
    for game in games:
        game_id, played_on, points_band, p1_id, p1_result, p2_id, p2_result = game

        r1, r2 = current_ratings[p1_id], current_ratings[p2_id]

        exp1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        exp2 = 1 - exp1

        if p1_result == 'win':
            act1, act2 = 1, 0
        elif p1_result == 'loss':
            act1, act2 = 0, 1
        else:
            act1, act2 = 0.5, 0.5

        new_r1 = r1 + k_factor * (act1 - exp1)
        new_r2 = r2 + k_factor * (act2 - exp2)

        # Insert into rating_history
        cursor.execute("""
            INSERT INTO rating_history (game_id, player_id, system_id,
                                        old_rating, new_rating, k_factor_used,
                                        expected_score, actual_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_id, p1_id, system_id, r1, new_r1, k_factor, exp1, act1))

        cursor.execute("""
            INSERT INTO rating_history (game_id, player_id, system_id,
                                        old_rating, new_rating, k_factor_used,
                                        expected_score, actual_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_id, p2_id, system_id, r2, new_r2, k_factor, exp2, act2))

        current_ratings[p1_id] = new_r1
        current_ratings[p2_id] = new_r2

    # Update ratings table
    for player_id, rating in current_ratings.items():
        games_played = cursor.execute("""
            SELECT COUNT(*)
            FROM game_participants gp
            JOIN games g ON gp.game_id = g.game_id
            WHERE gp.player_id = ? AND g.season_id = ? AND g.system_id = ?
        """, (player_id, season_id, system_id)).fetchone()[0]

        cursor.execute("""
            INSERT OR REPLACE INTO ratings (season_id, system_id, player_id,
                                            current_rating, last_updated)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (season_id, system_id, player_id, rating))


def process_ratings(season_id, system_id):
    """
    Wrapper to recalculate ratings for all points bands in a season/system.

    Args:
        season_id (int): The season identifier.
        system_id (int): The system identifier.

    Side effects:
        - Calls update_ratings_for_season for each points band.
        - Commits all changes to the database.
    """
    with sqlite3.connect("GPTLeague.db") as conn:
        cursor = conn.cursor()

        category_row = cursor.execute(
            "SELECT category FROM systems WHERE system_id = ?", (system_id,)
        ).fetchone()
        if not category_row:
            raise ValueError(f"No category found for system {system_id}")
        category = category_row[0]

        points_bands = cursor.execute(
            "SELECT DISTINCT points_band FROM elo_rules WHERE category = ?",
            (category,)
        ).fetchall()

        for pb in points_bands:
            update_ratings_for_season(season_id, system_id, category, conn, pb[0])

        conn.commit()
