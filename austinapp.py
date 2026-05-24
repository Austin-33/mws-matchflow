import os
from datetime import datetime
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# ─────────────────────────────
# EXTENSIONS
# ─────────────────────────────
db = SQLAlchemy()
login_manager = LoginManager()


# ─────────────────────────────
# CONFIG APP
# ─────────────────────────────
def create_app():

    app = Flask(__name__)

    # 🔐 SECURITY
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret")

    # 🗄️ DATABASE (Render PostgreSQL)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 📦 UPLOADS
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── INIT EXTENSIONS
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # ─────────────────────────────
    # MODELS
    # ─────────────────────────────
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ─────────────────────────────
    # BLUEPRINTS
    # ─────────────────────────────
    from routes.auth import auth_bp
    from routes.tournament import tournament_bp
    from routes.team import team_bp
    from routes.match import match_bp
    from routes.player import player_bp
    from routes.market import market_bp
    from routes.feed import feed_bp
    from routes.finance import finance_bp

    for bp in [
        auth_bp,
        tournament_bp,
        team_bp,
        match_bp,
        player_bp,
        market_bp,
        feed_bp,
        finance_bp
    ]:
        app.register_blueprint(bp)

    # ─────────────────────────────
    # DASHBOARD
    # ─────────────────────────────
    @app.route("/")
    def index():
        from models.tournament import Tournament
        from models.team import Team
        from models.match import Match

        tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
        teams = Team.query.all()

        today = datetime.utcnow().strftime("%Y-%m-%d")

        matches_today = Match.query.filter_by(date=today).all()

        return render_template(
            "dashboard.html",
            tournaments=tournaments,
            teams=teams,
            matches_today=matches_today
        )

    # ─────────────────────────────
    # INIT DB
    # ─────────────────────────────
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"[DB ERROR] {e}")

    return app


# ─────────────────────────────
# ENTRY POINT
# ─────────────────────────────
app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=True
    )