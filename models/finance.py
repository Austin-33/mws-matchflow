"""AUSTIN LEAGUE CORE — Finance & Awards Models."""
from datetime import datetime
from extensions import db


class TournamentAward(db.Model):
    """
    Prémio configurado para um torneio.
    award_type: 1st | 2nd | 3rd | top_scorer | top_assist | mvp | best_gk | fair_play | custom
    """
    __tablename__ = 'tournament_awards'

    id               = db.Column(db.Integer, primary_key=True)
    tournament_id    = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    award_type       = db.Column(db.String(30), nullable=False)
    label            = db.Column(db.String(100))
    prize_value      = db.Column(db.Float, default=0)
    prize_desc       = db.Column(db.String(200))
    is_active        = db.Column(db.Boolean, default=True)
    winner_team_id   = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    winner_player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    tournament   = db.relationship('Tournament', foreign_keys=[tournament_id],
                                   backref=db.backref('awards', lazy=True, cascade='all, delete-orphan'))
    winner_team  = db.relationship('Team',   foreign_keys=[winner_team_id])
    winner_player = db.relationship('Player', foreign_keys=[winner_player_id])

    AWARD_ICONS = {
        '1st':        '🥇',
        '2nd':        '🥈',
        '3rd':        '🥉',
        'top_scorer': '⚽',
        'top_assist': '🎯',
        'mvp':        '⭐',
        'best_gk':    '🧤',
        'fair_play':  '🤝',
        'custom':     '🏅',
    }
    AWARD_LABELS = {
        '1st':        '1º Lugar',
        '2nd':        '2º Lugar',
        '3rd':        '3º Lugar',
        'top_scorer': 'Melhor Marcador',
        'top_assist': 'Melhor Assistente',
        'mvp':        'MVP',
        'best_gk':    'Melhor Guarda-Redes',
        'fair_play':  'Fair Play',
        'custom':     'Prémio Especial',
    }

    @property
    def icon(self):
        return self.AWARD_ICONS.get(self.award_type, '🏅')

    @property
    def display_label(self):
        return self.label or self.AWARD_LABELS.get(self.award_type, self.award_type)

    @property
    def is_team_award(self):
        return self.award_type in ('1st', '2nd', '3rd')

    @property
    def is_player_award(self):
        return self.award_type in ('top_scorer', 'top_assist', 'mvp', 'best_gk', 'fair_play')

    def __repr__(self):
        return f'<TournamentAward {self.award_type} t={self.tournament_id}>'


class TeamPayment(db.Model):
    """Payment record for a team in a tournament."""
    __tablename__ = 'team_payments'

    id            = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    team_id       = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    payment_type  = db.Column(db.String(20), default='registration')
    # payment_type: registration | participation | penalty | other
    amount        = db.Column(db.Float, default=0)
    currency      = db.Column(db.String(10), default='KWZ')
    status        = db.Column(db.String(20), default='pending')
    # status: pending | paid | partial | waived
    paid_at       = db.Column(db.DateTime, nullable=True)
    notes         = db.Column(db.String(200))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    tournament = db.relationship('Tournament', foreign_keys=[tournament_id],
                                 backref=db.backref('payments', lazy=True, cascade='all, delete-orphan'))
    team       = db.relationship('Team', foreign_keys=[team_id],
                                 backref=db.backref('payments', lazy=True))

    STATUS_LABELS = {
        'pending':  '⏳ Pendente',
        'paid':     '✅ Pago',
        'partial':  '🔶 Parcial',
        'waived':   '🔵 Isento',
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def type_label(self):
        labels = {
            'registration':   'Inscrição',
            'participation':  'Taxa de Participação',
            'penalty':        'Penalização',
            'other':          'Outro',
        }
        return labels.get(self.payment_type, self.payment_type)

    def __repr__(self):
        return f'<TeamPayment {self.team_id} {self.payment_type} {self.status}>'
