"""Routes package - Blueprint registration."""
from routes.auth import auth_bp
from routes.leagues import leagues_bp
from routes.stats import stats_bp
from routes.admin import admin_bp
from routes.main import main_bp

def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(leagues_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
