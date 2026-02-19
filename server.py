"""
Warhammer 40k League Application
Main Flask application entry point and configuration.
"""
import logging
import os
import secrets
import sqlite3

from flask import Flask, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from routes import register_blueprints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
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

    # SECRET_KEY - critical for session security
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Session configuration
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    Session(app)

    # CSRF protection
    CSRFProtect(app)

    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
    app.limiter = limiter

    # Register blueprints
    register_blueprints(app)
    
    # Register context processors
    app.context_processor(inject_systems)
    app.context_processor(inject_current_user)
    
    # Register after_request handler
    @app.after_request
    def after_request(response):
        """Ensure responses aren't cached and add security headers."""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    
    return app


app = create_app()


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug_mode)
