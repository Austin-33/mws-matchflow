from extensions import db
from datetime import datetime


class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)

    # ─── Identidade ───────────────────────────────────────────
    name = db.Column(db.String(100), unique=True, nullable=False)
    short_name = db.Column(db.String(10))
    founded_date = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Portugal')
    primary_color = db.Column(db.String(10), default='#2563eb')
    secondary_color = db.Column(db.String(10), default='#ffffff')
    logo_url = db.Column(db.String(300), default='')      # path to uploaded logo
    stadium = db.Column(db.String(100))

    # ─── Direcção ─────────────────────────────────────────────
    ceo = db.Column(db.String(100))
    manager = db.Column(db.String(100))
    coach = db.Column(db.String(100))
    assistant_coach = db.Column(db.String(100))
    captain = db.Column(db.String(100))

    # ─── Jogo ─────────────────────────────────────────────────
    formation = db.Column(db.String(20), default='4-3-3')
    tactic = db.Column(db.String(200))
    sport = db.Column(db.String(30), default='futsal')

    # ─── Contacto ─────────────────────────────────────────────
    email = db.Column(db.String(150))
    phone = db.Column(db.String(30))
    website = db.Column(db.String(200))
    instagram = db.Column(db.String(100))

    # ─── Meta ─────────────────────────────────────────────────
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now())

    players = db.relationship('Player', backref='team', lazy=True, cascade='all, delete-orphan')
    posts = db.relationship('TeamPost', backref='team', lazy=True, cascade='all, delete-orphan',
                            order_by='TeamPost.created_at.desc()')

    @property
    def initials(self):
        words = self.name.split()
        if len(words) >= 2:
            return (words[0][0] + words[-1][0]).upper()
        return self.name[:2].upper()

    @property
    def logo_or_initials(self):
        return self.logo_url if self.logo_url else None

    def __repr__(self):
        return f'<Team {self.name}>'


class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)

    # ─── Identidade ───────────────────────────────────────────
    name = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(50))
    number = db.Column(db.Integer)
    position = db.Column(db.String(50))
    secondary_position = db.Column(db.String(50))
    photo_url = db.Column(db.String(300), default='')     # path to uploaded photo

    # ─── Dados pessoais ───────────────────────────────────────
    birth_date = db.Column(db.String(20))
    age = db.Column(db.Integer)
    nationality = db.Column(db.String(50))
    id_number = db.Column(db.String(30))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(150))

    # ─── Físico ───────────────────────────────────────────────
    height_cm = db.Column(db.Integer)
    weight_kg = db.Column(db.Integer)
    dominant_foot = db.Column(db.String(10), default='Direito')

    # ─── Contrato ─────────────────────────────────────────────
    status = db.Column(db.String(20), default='ativo')
    contract_start = db.Column(db.String(20))
    contract_end = db.Column(db.String(20))

    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    # ─── Estatísticas agregadas ───────────────────────────────
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    yellow_cards = db.Column(db.Integer, default=0)
    red_cards = db.Column(db.Integer, default=0)
    matches_played = db.Column(db.Integer, default=0)
    minutes_played = db.Column(db.Integer, default=0)

    match_stats = db.relationship('PlayerMatchStat', backref='player', lazy=True, cascade='all, delete-orphan')

    @property
    def display_name(self):
        return self.nickname if self.nickname else self.name

    def __repr__(self):
        return f'<Player {self.name}>'


class TeamPost(db.Model):
    """Posts/updates from team members."""
    __tablename__ = 'team_posts'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))
    post_type = db.Column(db.String(20), default='update')  # update | result | lineup | news
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', foreign_keys=[author_id])

    def __repr__(self):
        return f'<TeamPost team={self.team_id}>'
