from extensions import db
from datetime import datetime


class Tournament(db.Model):
    __tablename__ = 'tournaments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sport = db.Column(db.String(50), default='futsal')
    type = db.Column(db.String(50), nullable=False)
    format_type = db.Column(db.String(20), default='liga')
    status = db.Column(db.String(20), default='pending')

    # ─── Criador ──────────────────────────────────────────────
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    teams_count = db.Column(db.Integer, default=0)       # max teams expected
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(300), default='')

    # ─── Fase de Grupos ───────────────────────────────────────
    has_groups = db.Column(db.Boolean, default=False)
    groups_count = db.Column(db.Integer, default=0)
    teams_per_group = db.Column(db.Integer, default=0)
    qualify_per_group = db.Column(db.Integer, default=2)
    group_legs = db.Column(db.Integer, default=1)        # 1 = uma volta, 2 = duas voltas

    # ─── Fase Eliminatória ────────────────────────────────────
    has_knockout = db.Column(db.Boolean, default=False)
    has_round_of_16 = db.Column(db.Boolean, default=False)
    has_quarter = db.Column(db.Boolean, default=False)
    has_semi = db.Column(db.Boolean, default=True)
    has_final = db.Column(db.Boolean, default=True)
    knockout_legs = db.Column(db.Integer, default=1)     # 1 = jogo único, 2 = ida e volta

    start_date = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=db.func.now())

    # ─── Financeiro ───────────────────────────────────────────
    currency           = db.Column(db.String(10), default='KWZ')
    registration_fee   = db.Column(db.Float, default=0)   # taxa de inscrição por equipa
    participation_fee  = db.Column(db.Float, default=0)   # taxa de participação por equipa
    prize_pool_total   = db.Column(db.Float, default=0)   # total do prémio

    groups = db.relationship('Group', backref='tournament', lazy=True, cascade='all, delete-orphan')
    teams = db.relationship('TournamentTeam', backref='tournament', lazy=True, cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='tournament', lazy=True, cascade='all, delete-orphan')

    @property
    def sport_label(self):
        return '⚽ Futsal' if self.sport == 'futsal' else '🏟️ Futebol 11'

    @property
    def knockout_phases(self):
        phases = []
        if self.has_round_of_16:
            phases.append(('round_of_16', 'Oitavos de Final'))
        if self.has_quarter:
            phases.append(('quarter', 'Quartos de Final'))
        if self.has_semi:
            phases.append(('semi', 'Meia-Final'))
        if self.has_final:
            phases.append(('final', '🏆 Final'))
        return phases

    @property
    def registered_teams_count(self):
        return TournamentTeam.query.filter_by(tournament_id=self.id).count()

    @property
    def spots_remaining(self):
        if not self.teams_count:
            return None
        return max(0, self.teams_count - self.registered_teams_count)

    def __repr__(self):
        return f'<Tournament {self.name}>'


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)

    group_teams = db.relationship('TournamentTeam', backref='group', lazy=True)

    def __repr__(self):
        return f'<Group {self.name}>'


class TournamentTeam(db.Model):
    __tablename__ = 'tournament_teams'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    group_letter = db.Column(db.String(5))
    phase = db.Column(db.String(30), default='group')
    seed = db.Column(db.Integer, default=0)              # seed for draw

    # ─── Standings ────────────────────────────────────────────
    played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    goals_for = db.Column(db.Integer, default=0)
    goals_against = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)

    team = db.relationship('Team', backref='tournament_entries')

    @property
    def goal_diff(self):
        return self.goals_for - self.goals_against

    def __repr__(self):
        return f'<TournamentTeam {self.team_id} in {self.tournament_id}>'
