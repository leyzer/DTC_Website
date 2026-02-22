"""Authentication routes: login, register, logout, password reset."""
import sqlite3
import secrets
import logging
from datetime import datetime, timedelta
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from helpers import apology, hash_password, check_password, check_account, CURRENT_YEAR, validate_password_strength, is_admin

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            username = request.form.get("username", "").lower()
            password = request.form.get("password", "")
            
            if not username:
                return apology("username required", 200)
            elif not password:
                return apology("must provide password", 400)

            with sqlite3.connect('GPTLeague.db') as connection:
                cursor = connection.cursor()
                row = cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (username,)).fetchone()

            if not row or check_account(username, password) == False:
                return apology("incorrect username or password", 400)

            session["user_id"] = row[0]
            logger.info(f"User {username} logged in successfully")
            return redirect("/")
        
        except Exception as e:
            logger.error(f"Login error for user {request.form.get('username', 'unknown')}: {str(e)}")
            return apology("An error occurred during login", 400)

    else:
        # Get user count for conditional registration visibility
        try:
            with sqlite3.connect('GPTLeague.db') as connection:
                cursor = connection.cursor()
                user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        except:
            user_count = 0
        
        return render_template("login.html", user_count=user_count)


@auth_bp.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    try:
        with sqlite3.connect('GPTLeague.db') as connection:
            cursor = connection.cursor()
            user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        
        # Only allow registration if no users exist
        if user_count > 0:
            flash("User registration is closed. Please contact an administrator.", "warning")
            return redirect(url_for('auth.login'))
    
    except Exception as e:
        logger.error(f"Error checking user count: {str(e)}")
        flash("An error occurred", "danger")
        return redirect(url_for('auth.login'))
    
    if request.method == "POST":
        try:
            username = request.form.get("username", "").lower().strip()
            email = request.form.get("email", "").lower().strip()

            if not username or not email:
                flash("Username and email are required", "warning")
                return redirect("/register")

            fullname = request.form.get("fullname", "").strip()
            if not fullname:
                flash('Full name is required', 'warning')
                return redirect("/register")
            fullname = fullname.title()

            password = request.form.get("password", "")
            confirmation = request.form.get("confirmation", "")

            if not password or not confirmation:
                flash('Password and confirmation are required', 'warning')
                return redirect("/register")
            
            if password != confirmation:
                flash('Password and confirmation do not match', 'warning')
                return redirect("/register")

            # Validate password strength
            is_valid, message = validate_password_strength(password)
            if not is_valid:
                flash(f'Password validation failed: {message}', 'warning')
                return redirect("/register")

            with sqlite3.connect('GPTLeague.db') as connection:
                connection.row_factory = sqlite3.Row
                cursor = connection.cursor()

                existing_user = cursor.execute(
                    "SELECT * FROM users WHERE user_name = ? OR email = ?",
                    (username, email)
                ).fetchone()

                if existing_user:
                    if existing_user["user_name"] == username:
                        flash("Username already exists", "warning")
                    elif existing_user["email"] == email:
                        flash("Email already exists", "warning")
                    return redirect("/register")

                hashed_password = hash_password(password)
                cursor.execute("INSERT INTO users (user_name, full_name, email, password_hash) VALUES (?,?,?,?)",
                (username, fullname, email, hashed_password))
                userID = cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (username,)).fetchone()
                
                # Assign role: first user is admin, others are user
                role = 'admin' if userID[0] == 1 else 'user'
                cursor.execute("INSERT INTO user_roles (user_id, role) VALUES (?, ?)", (userID[0], role))
                
                connection.commit()
                logger.info(f"New user registered: {username}")

            flash("Registered successfully!", "success")
            return redirect("/")

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration', 'danger')
            return redirect(url_for('auth.register'))
    else:
        return render_template("register.html", user_count=user_count)


@auth_bp.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    from helpers import login_required
    
    @login_required
    def _reset_password_handler():
        user_id = int(session["user_id"])
        try:
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

                # Validate password strength
                is_valid, message = validate_password_strength(password)
                if not is_valid:
                    flash(f'Password validation failed: {message}', 'warning')
                    return redirect("reset_password.html")

                with sqlite3.connect('GPTLeague.db') as connection:
                    cursor = connection.cursor()
                    hashed_password = hash_password(password)
                    cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (hashed_password, user_id))
                    connection.commit()
                    logger.info(f"Password reset for user_id {user_id}")
                
                flash("Password updated successfully!", "success")
                return redirect("/profile")              

        except Exception as e:
            logger.error(f"Password reset error for user_id {user_id}: {str(e)}")
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
            # Check if user is admin
            user_id = session.get("user_id")
            if not is_admin(user_id):
                return apology("Admin access required", 403)
            
            current_year = CURRENT_YEAR()
            next_year = current_year + 1
            
            if request.method == "GET":  
                return render_template("endseason.html", current_year=current_year, next_year=next_year) 
            else:
                # POST request - actually end the season
                confirm = request.form.get("confirm")
                
                if not confirm:
                    return apology("You must confirm to end the season", 400)
                
                with sqlite3.connect('GPTLeague.db') as connection:
                    cursor = connection.cursor()
                    
                    # Archive the current season
                    cursor.execute("UPDATE seasons SET status = 'archived' WHERE year = ?", (current_year,))
                    
                    # Create the new season
                    start = f"{next_year}-02-01 00:00:00"  
                    end = f"{next_year}-12-31 23:59:59"
                    cursor.execute("INSERT INTO seasons (name, year, start_date, end_date, status) VALUES (?,?,?,?,'active')", (f"Season {next_year}", next_year, start, end))
                    connection.commit()
                    logger.info(f"Season {current_year} archived and new season {next_year} created by admin {user_id}")
                    flash(f'Season {current_year} archived. New season {next_year} has been created.', 'success')
                
                return redirect("/profile")
        except Exception as e:
            logger.error(f"Error ending season: {str(e)}")
            flash('An error occurred ending season', 'warning')
            return apology("An error occurred ending season", 400)
    
    return _endseason_handler()

@auth_bp.route("/claim_account", methods=["GET", "POST"])
def claim_account():
    """Allow users with provisional accounts to set their password and claim their account"""
    if request.method == "POST":
        try:
            username = request.form.get("username", "").lower().strip()
            temp_password = request.form.get("temp_password", "")
            new_password = request.form.get("new_password", "")
            confirmation = request.form.get("confirmation", "")

            if not all([username, temp_password, new_password, confirmation]):
                flash("All fields are required", "warning")
                return redirect("/claim_account")

            with sqlite3.connect('GPTLeague.db') as connection:
                connection.row_factory = sqlite3.Row
                cursor = connection.cursor()

                # Find user
                user = cursor.execute(
                    "SELECT user_id, password_hash, is_provisional FROM users WHERE user_name = ?",
                    (username,)
                ).fetchone()

                if not user:
                    flash("Username not found", "warning")
                    return redirect("/claim_account")

                if not user["is_provisional"]:
                    flash("This account has already been claimed", "warning")
                    return redirect("/login")

                # Verify temporary password
                if not check_password(temp_password, user["password_hash"]):
                    logger.warning(f"Failed claim attempt for user {username} - incorrect temp password")
                    flash("Incorrect temporary password", "warning")
                    return redirect("/claim_account")

                # Validate new password
                is_valid, message = validate_password_strength(new_password)
                if not is_valid:
                    flash(f'Password validation failed: {message}', 'warning')
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
                logger.info(f"Account claimed for user {username}")

            flash("Account claimed successfully! You can now log in with your new password.", "success")
            return redirect("/login")

        except Exception as e:
            logger.error(f"Error claiming account for user {request.form.get('username', 'unknown')}: {str(e)}")
            flash("An error occurred claiming your account", "warning")
            return redirect("/claim_account")

    return render_template("claim_account.html")