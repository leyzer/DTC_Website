"""
Warhammer 40k League Application
Main Flask application entry point and configuration.
"""
import os
import sqlite3
import logging
from flask import Flask, session
from flask_session import Session
from routes import register_blueprints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Scoring constants (base of 100 values)
MAXVALUE_PAINTED = 10
MAXVALUE_WYSIWYG = 10
MAXVALUE_GENERALSHIP = 40
MAXVALUE_GAMESPLAYED = 10
MAXVALUE_UNIQUE = 30


def inject_systems():
    """Inject available systems into template context."""
    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        systems_list = cursor.execute("SELECT system_id, system_name FROM systems").fetchall()
    return dict(systems=systems_list)


def inject_current_user():
    """Inject current user info into template context."""
    if 'user_id' in session:
        with sqlite3.connect("GPTLeague.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            user = cursor.execute(
                "SELECT user_id, user_name FROM users WHERE user_id = ?",
                (session['user_id'],)
            ).fetchone()
            role = cursor.execute(
                "SELECT 1 FROM user_roles WHERE user_id = ? AND role = 'admin'",
                (session['user_id'],)
            ).fetchone()

        if user:
            return dict(current_user={
                "user_id": user["user_id"],
                "user_name": user["user_name"],
                "is_admin": role is not None
            })
    
    return dict(current_user=None)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure session
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    Session(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register context processors
    app.context_processor(inject_systems)
    app.context_processor(inject_current_user)
    
    # Register after_request handler
    @app.after_request
    def after_request(response):
        """Ensure responses aren't cached"""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response
    
    return app


app = create_app()


if __name__ == "__main__":
    # Only enable debug mode in development
    debug_mode = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(debug=debug_mode)
