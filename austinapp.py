import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for
from extensions import db, login_manager

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─────────────────────────────
# CONFIG APP
# ─────────────────────────────
def create_app():

    app = Flask(__name__)

    # 🔐 SECURITY
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret_austin_2024")

    # 🗄️ DATABASE — PostgreSQL em produção, SQLite localmente
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Render fornece postgres://, SQLAlchemy 2.x precisa de postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(base_dir, 'instance', 'database.db')}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 📦 UPLOADS
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    for sub in ("logos", "players", "posts"):
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], sub), exist_ok=True)

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
    # CONTEXT PROCESSORS
    # ─────────────────────────────
    @app.context_processor
    def inject_globals():
        from datetime import date
        return {'now_date': date.today().strftime('%Y-%m-%d')}

    # ─────────────────────────────
    # DASHBOARD
    # ─────────────────────────────
    @app.route("/")
    def index():
        from flask_login import current_user
        # Se não autenticado → redireciona para login
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

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
        port=int(os.getenv("PORT", 5026)),
        debug=True
    )