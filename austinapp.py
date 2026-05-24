import os
from datetime import datetime

from flask import Flask, render_template
from flask_login import login_required

from extensions import db, login_manager


# ─────────────────────────────────────────────
# BASE PATHS
# ─────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

INSTANCE_FOLDER = os.path.join(BASE_DIR, "instance")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(INSTANCE_FOLDER, "database.db")
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─────────────────────────────────────────────
# APP FACTORY
# ─────────────────────────────────────────────
def create_app():

    app = Flask(__name__)

    # ── CONFIG ────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "dev_secret_change_me"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB

    # ── CREATE FOLDERS ────────────────────────
    os.makedirs(INSTANCE_FOLDER, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # ── EXTENSIONS ────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"

    # ─────────────────────────────────────────
    # BLUEPRINTS
    # ─────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.tournament import tournament_bp
    from routes.team import team_bp
    from routes.match import match_bp
    from routes.player import player_bp
    from routes.market import market_bp
    from routes.feed import feed_bp
    from routes.finance import finance_bp

    blueprints = [
        auth_bp,
        tournament_bp,
        team_bp,
        match_bp,
        player_bp,
        market_bp,
        feed_bp,
        finance_bp
    ]

    for bp in blueprints:
        app.register_blueprint(bp)

    # ─────────────────────────────────────────
    # USER LOADER
    # ─────────────────────────────────────────
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    # ─────────────────────────────────────────
    # DASHBOARD ROUTE
    # ─────────────────────────────────────────
    @app.route("/")
    @login_required
    def index():

        from models.tournament import Tournament
        from models.team import Team
        from models.match import Match

        tournaments = Tournament.query.order_by(
            Tournament.created_at.desc()
        ).all()

        teams = Team.query.all()

        today = datetime.utcnow().strftime("%Y-%m-%d")

        matches_today = Match.query.filter_by(
            date=today
        ).all()

        return render_template(
            "dashboard.html",
            tournaments=tournaments,
            teams=teams,
            matches_today=matches_today
        )

    # ─────────────────────────────────────────
    # DATABASE INIT (SAFE)
    # ─────────────────────────────────────────
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"[DB INIT ERROR] {e}")

    return app


# ─────────────────────────────────────────────
# APP INSTANCE
# ─────────────────────────────────────────────
app = create_app()


# ─────────────────────────────────────────────
# DEV RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )