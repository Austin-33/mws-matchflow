import os
from datetime import datetime

from flask import Flask, render_template
from flask_login import login_required

from extensions import db, login_manager

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_BASE_DIR, 'instance', 'database.db')
UPLOAD_FOLDER = os.path.join(_BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'alc_secret_2026'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{_DB_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # ─── Register Blueprints ──────────────────────────────────
    from routes.auth import auth_bp
    from routes.tournament import tournament_bp
    from routes.team import team_bp
    from routes.match import match_bp
    from routes.player import player_bp
    from routes.market import market_bp
    from routes.feed import feed_bp
    from routes.finance import finance_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tournament_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(match_bp)
    app.register_blueprint(player_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(finance_bp)

    # ─── User loader ──────────────────────────────────────────
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ─── Main Dashboard ───────────────────────────────────────
    @app.route('/')
    @login_required
    def index():
        from models.tournament import Tournament
        from models.team import Team
        from models.match import Match

        tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
        teams = Team.query.all()
        today = datetime.today().strftime('%Y-%m-%d')
        matches_today = Match.query.filter_by(date=today).all()
        return render_template('dashboard.html',
                               tournaments=tournaments,
                               teams=teams,
                               matches_today=matches_today)

    return app


    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)