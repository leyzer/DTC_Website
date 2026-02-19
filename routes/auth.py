"""Authentication routes: login, register, logout, password reset."""
import logging
import sqlite3
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, current_app
from helpers import (apology, hash_password, check_password, check_account, CURRENT_YEAR,
                     is_valid_email, sanitize_username, sanitize_name, validate_password_strength)

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    limiter = current_app.limiter
    
    @limiter.limit("10 per minute")
    def _login_post():
        try:
            connection = sqlite3.connect('GPTLeague.db')
            cursor = connection.cursor()

            username = request.form.get("username", "").lower().strip()
            password = request.form.get("password", "")
            
            if not username:
                return apology("username required", 200)
            elif not password:
                return apology("must provide password", 400)

            row = cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (username,)).fetchone()

            if not row or not check_account(username, password):
                return apology("Invalid username or password", 400)

            session["user_id"] = row[0]
            return redirect("/")
        
        except Exception:
            logger.error("Error during login")
            return apology("An error occurred during login", 400)
        finally:    
            if connection:
                connection.close()

    if request.method == "POST":
        return _login_post()
    else:
        return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    limiter = current_app.limiter

    @limiter.limit("5 per hour")
    def _register_post():
        try:
            connection = sqlite3.connect('GPTLeague.db')
            cursor = connection.cursor()

            username = sanitize_username(request.form.get("username", ""))
            if not username:
                flash("Invalid username format. Use only letters, numbers, and underscores (max 50 chars).", "warning")
                return redirect("/register")

            email = request.form.get("email", "").lower().strip()
            if not is_valid_email(email):
                flash("Invalid email format", "warning")
                return redirect("/register")

            fullname = sanitize_name(request.form.get("fullname", ""))
            if not fullname:
                flash("Invalid name format. Use only letters, spaces, hyphens, and apostrophes.", "warning")
                return redirect("/register")

            existing_user = cursor.execute(
                "SELECT * FROM users WHERE user_name = ? OR email = ?",
                (username, email)
            ).fetchone()

            if existing_user:
                flash("Username or email already registered", "warning")
                return redirect("/register")

            password = request.form.get("password", "")
            confirmation = request.form.get("confirmation", "")

            if not password or not confirmation:
                flash('Password and confirmation are required', 'warning')
                return redirect("/register")
            if password != confirmation:
                flash('Password and confirmation do not match', 'warning')
                return redirect("/register")

            is_valid, error_msg = validate_password_strength(password)
            if not is_valid:
                flash(error_msg, 'warning')
                return redirect("/register")

            hashed_password = hash_password(password)
            cursor.execute("INSERT INTO users (user_name, full_name, email, password_hash) VALUES (?,?,?,?)",
            (username, fullname.title(), email, hashed_password))
            userID = cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (username,)).fetchone()
            
            # Assign role: first user is admin, others are user
            role = 'admin' if userID[0] == 1 else 'user'
            cursor.execute("INSERT INTO user_roles (user_id, role) VALUES (?, ?)", (userID[0], role))
            
            connection.commit()
            cursor.close()        
            connection.close()

            flash("Registered successfully!", "success")
            return redirect("/")

        except Exception:
            logger.error("Error during registration")
            flash('An error occurred during registration', 'danger')
            return redirect(url_for('auth.register'))
        finally:
            if connection:
                connection.close()

    if request.method == "POST":
        return _register_post()
    else:
        return render_template("register.html")


@auth_bp.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    from helpers import login_required
    
    @login_required
    def _reset_password_handler():
        user_id = int(session["user_id"])
        try:
            with sqlite3.connect('GPTLeague.db') as connection:
                cursor = connection.cursor()
                if request.method == "GET":  
                    return render_template("reset_password.html") 
                else:
                    password = request.form.get("password", "")
                    confirmation = request.form.get("confirmation", "")

                    if not password or not confirmation:
                        flash('Password and confirmation are required', 'warning')
                        return redirect("reset_password.html")
                    if password != confirmation:
                        flash('Password and confirmation do not match', 'warning')
                        return redirect("reset_password.html")

                    is_valid, error_msg = validate_password_strength(password)
                    if not is_valid:
                        flash(error_msg, 'warning')
                        return redirect(url_for('auth.reset_password'))

                    hashed_password = hash_password(password)
                    cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (hashed_password, user_id))
                    connection.commit()
                
                return redirect("/profile")              

        except Exception:
            logger.error("Error resetting password")
            flash('An error occurred resetting password', 'warning')
            return apology("An error occurred resetting password", 400)
    
    return _reset_password_handler()


@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    """Forgot password feature is disabled - users should contact admin."""
    flash('Password reset requests are managed by administrators. Please contact an admin for password assistance.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_with_token(token):
    """Password reset feature is disabled - users should contact admin."""
    flash('Password reset requests are managed by administrators. Please contact an admin for password assistance.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route("/endseason", methods=["GET", "POST"])
def endseason():
    from helpers import login_required
    
    @login_required
    def _endseason_handler():
        try:
            with sqlite3.connect('GPTLeague.db') as connection:
                cursor = connection.cursor()
                if request.method == "GET":  
                    return render_template("endseason.html") 
                else:
                    username = request.form.get("username")
                    password = request.form.get("password")
                    endseason = request.form.get("endseason")

                    if not username:
                        return apology("username required", 200)
                    elif not password:
                        return apology("must provide password", 400)
                   
                    if check_account(username, password) == False:
                        return apology("incorrect username or Password", 400)
                    
                    if endseason:
                        year = CURRENT_YEAR()
                        year += 1
                        start = f"{year}-01-01"  
                        end = f"{year}-12-31"
                        cursor.execute("INSERT INTO seasons (name, year, start_date, end_date) VALUES (?,?,?,?)", (f"{year} League", year, start, end))
                        connection.commit()
                    
                    return redirect("/profile")
        except Exception:
            logger.error("Error ending season")
            flash('An error occurred ending season', 'warning')
            return apology("An error occurred ending season", 400)
    
    return _endseason_handler()

@auth_bp.route("/claim_account", methods=["GET", "POST"])
def claim_account():
    """Allow users with provisional accounts to set their password and claim their account"""
    if request.method == "POST":
        try:
            connection = sqlite3.connect('GPTLeague.db')
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            username = request.form.get("username", "").lower().strip()
            temp_password = request.form.get("temp_password", "")
            new_password = request.form.get("new_password", "")
            confirmation = request.form.get("confirmation", "")

            if not all([username, temp_password, new_password, confirmation]):
                flash("All fields are required", "warning")
                return redirect("/claim_account")

            # Find user
            user = cursor.execute(
                "SELECT user_id, password_hash, is_provisional FROM users WHERE user_name = ?",
                (username,)
            ).fetchone()

            if not user or not user["is_provisional"]:
                flash("Invalid username or account status", "warning")
                return redirect("/claim_account")

            # Verify temporary password
            if not check_password(temp_password, user["password_hash"]):
                flash("Invalid credentials", "warning")
                return redirect("/claim_account")

            # Validate new password strength
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                flash(error_msg, "warning")
                return redirect("/claim_account")

            if new_password != confirmation:
                flash("New password and confirmation do not match", "warning")
                return redirect("/claim_account")

            # Update password and mark as claimed
            hashed_new_password = hash_password(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = ?, is_provisional = 0 WHERE user_id = ?",
                (hashed_new_password, user["user_id"])
            )
            connection.commit()

            flash("Account claimed successfully! You can now log in with your new password.", "success")
            return redirect("/login")

        except Exception:
            logger.error("Error claiming account")
            flash("An error occurred claiming your account", "warning")
            return redirect("/claim_account")
        finally:
            if connection:
                connection.close()

    return render_template("claim_account.html")