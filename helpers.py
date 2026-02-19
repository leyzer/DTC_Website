import bcrypt
import logging
import re
import sqlite3

from flask import redirect, render_template, session
from functools import wraps

logger = logging.getLogger(__name__)

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def hash_password(password):
    # Hash a password for the first time
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password

def check_password(password, hashed_password):
    # Check hashed password against entered password
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def is_valid_email(email):
    """Validate email format with robust regex."""
    if not email or len(email) > 254:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_username(username):
    """Sanitize username - alphanumeric and underscore only."""
    if not username or len(username) > 50:
        return None
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return None
    return username.lower().strip()


def sanitize_name(name):
    """Sanitize full name - remove dangerous characters."""
    if not name or len(name) > 100:
        return None
    if not re.match(r'^[a-zA-Z\s\-\']+$', name):
        return None
    return name.strip()


def validate_password_strength(password):
    """
    Validate password meets security requirements.
    Returns (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, ""


def CURRENT_YEAR():
    """Return the most recent year from the `seasons` table in GPTLeague.db.

    Note: older code referenced `league.db` and the singular `season` table.
    The application uses `GPTLeague.db` and `seasons` elsewhere; prefer that.
    """
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            cursor = connection.cursor()
            year = cursor.execute("SELECT year FROM seasons ORDER BY year DESC LIMIT 1").fetchone()
            return year[0] if year else None
    except Exception:
        logger.error("Database error in CURRENT_YEAR")
        return None

def season(year):
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            cursor = connection.cursor()
            season = cursor.execute("SELECT season_id,start_date,end_date FROM seasons WHERE year = ?", (year,)).fetchone()
            if season:
                start = season[1]
                end = season[2]
                return (start,end) 
            else:
                return None
            
    except Exception:
        logger.error("Database error in season")
        return None     
    
def all_seasons():
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            return cursor.execute(
                "SELECT year FROM seasons WHERE status IN ('active','archived') ORDER BY year DESC"
            ).fetchall()
    except Exception:
        logger.error("Database error in all_seasons")
        return []
 
    

def check_account(username, password):
    """Verify username/password against `users.hash` in GPTLeague.db.

    This function normalizes to the `username` column (server.py uses
    `username`) and reads the `hash` column. It returns `True` for a
    successful match, `False` for failure.
    """
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            cursor = connection.cursor()
            row = cursor.execute("SELECT password_hash FROM users WHERE user_name = ?", (username,)).fetchone()
            if not row:
                return False
            stored_hash = row[0]
            # sqlite may return the stored hash as text or bytes
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode('utf-8')
            return check_password(password, stored_hash)
    except Exception:
        logger.error("Database error in check_account")
        return False
    

def is_admin(user_id):
    with sqlite3.connect("GPTLeague.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        role = cursor.execute(
            "SELECT 1 FROM user_roles WHERE user_id = ? AND role = 'admin'",
            (user_id,)
        ).fetchone()
        return role is not None

