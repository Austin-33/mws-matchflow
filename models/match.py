from extensions import db
from datetime import datetime


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    team1_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    date = db.Column(db.String(20))
    time = db.Column(db.String(10), default='15:00')
    venue = db.Column(db.String(100))
    round_number = db.Column(db.Integer, default=1)

    # phase: group | round_of_16 | quarter | semi | final
    phase = db.Column(db.String(30), default='group')
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    group_letter = db.Column(db.String(5))

    # ─── Result ───────────────────────────────────────────────
    score1 = db.Column(db.Integer, nullable=True)
    score2 = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled | live | finished | cancelled

    # ─── Criador / controlo ───────────────────────────────────
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    # ─── Match duration (minutes played) ──────────────────────
    minute_current = db.Column(db.Integer, default=0)

    team1 = db.relationship('Team', foreign_keys=[team1_id], backref='home_matches')
    team2 = db.relationship('Team', foreign_keys=[team2_id], backref='away_matches')
    player_stats = db.relationship('PlayerMatchStat', backref='match', lazy=True, cascade='all, delete-orphan')
    events = db.relationship('MatchEvent', backref='match', lazy=True, cascade='all, delete-orphan',
                             order_by='MatchEvent.minute')
    lineups = db.relationship('MatchLineup', backref='match', lazy=True, cascade='all, delete-orphan')

    @property
    def score_display(self):
        if self.score1 is not None and self.score2 is not None:
            return f'{self.score1} - {self.score2}'
        return 'vs'

    @property
    def phase_label(self):
        labels = {
            'group': f'Grupo {self.group_letter or ""}',
            'round_of_16': 'Oitavos de Final',
            'quarter': 'Quartos de Final',
            'semi': 'Meia-Final',
            'final': '🏆 Final',
        }
        return labels.get(self.phase, self.phase)

    def __repr__(self):
        return f'<Match {self.team1_id} vs {self.team2_id} on {self.date}>'


class PlayerMatchStat(db.Model):
    __tablename__ = 'player_match_stats'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    yellow_cards = db.Column(db.Integer, default=0)
    red_cards = db.Column(db.Integer, default=0)
    minutes_played = db.Column(db.Integer, default=40)

    def __repr__(self):
        return f'<PlayerMatchStat player={self.player_id} match={self.match_id}>'


class MatchEvent(db.Model):
    """Live match events: goals, cards, fouls, substitutions."""
    __tablename__ = 'match_events'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    minute = db.Column(db.Integer, default=0)
    # event_type: goal | yellow_card | red_card | foul | foul_yellow | foul_red | substitution | penalty | own_goal
    event_type = db.Column(db.String(30), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    player2_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)  # assist / sub-in
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship('Team', foreign_keys=[team_id])
    player = db.relationship('Player', foreign_keys=[player_id], backref='events')
    player2 = db.relationship('Player', foreign_keys=[player2_id])

    EVENT_ICONS = {
        'goal': '⚽',
        'own_goal': '🥅',
        'yellow_card': '🟨',
        'red_card': '🟥',
        'foul': '⚠️',
        'foul_yellow': '⚠️🟨',
        'foul_red': '⚠️🟥',
        'substitution': '🔄',
        'penalty': '🎯',
    }

    @property
    def icon(self):
        return self.EVENT_ICONS.get(self.event_type, '📋')

    def __repr__(self):
        return f'<MatchEvent {self.event_type} min={self.minute}>'


class MatchLineup(db.Model):
    """Starting eleven and substitutes for each team in a match."""
    __tablename__ = 'match_lineups'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    is_starter = db.Column(db.Boolean, default=True)   # True=titular, False=suplente
    position_override = db.Column(db.String(20))        # position for this match
    shirt_number = db.Column(db.Integer)
    formation = db.Column(db.String(20))                # formation used

    team = db.relationship('Team', foreign_keys=[team_id])
    player = db.relationship('Player', foreign_keys=[player_id], backref='lineups')

    def __repr__(self):
        return f'<MatchLineup match={self.match_id} player={self.player_id}>'
