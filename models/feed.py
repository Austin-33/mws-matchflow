"""
AUSTIN LEAGUE CORE — Feed System
FeedPost: publicações globais, de campeonato e de equipa.
FeedPostTeam: relação many-to-many entre posts e equipas marcadas.
"""
from datetime import datetime
from extensions import db


class FeedPost(db.Model):
    """
    Post universal do feed.
    post_type:
      result    — resultado automático de jogo terminado
      announce  — anúncio da organização
      news      — notícia geral
      lineup    — convocatória
      highlight — destaque / momento do jogo
    scope:
      global      — aparece em todo o lado
      tournament  — só no feed do campeonato
      team        — só no feed das equipas marcadas
    """
    __tablename__ = 'feed_posts'

    id = db.Column(db.Integer, primary_key=True)

    # ─── Conteúdo ─────────────────────────────────────────────
    post_type = db.Column(db.String(20), default='news')
    scope = db.Column(db.String(20), default='global')
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))

    # ─── Contexto ─────────────────────────────────────────────
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # ─── Meta ─────────────────────────────────────────────────
    is_pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ─── Relações ─────────────────────────────────────────────
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id],
                                 backref=db.backref('feed_posts', lazy=True))
    match = db.relationship('Match', foreign_keys=[match_id],
                            backref=db.backref('feed_post', uselist=False))
    author = db.relationship('User', foreign_keys=[author_id])
    tagged_teams = db.relationship('FeedPostTeam', backref='post', lazy=True,
                                   cascade='all, delete-orphan')

    @property
    def type_icon(self):
        icons = {
            'result':    '🏆',
            'announce':  '📢',
            'news':      '📰',
            'lineup':    '📋',
            'highlight': '⭐',
        }
        return icons.get(self.post_type, '📋')

    @property
    def type_label(self):
        labels = {
            'result':    'Resultado',
            'announce':  'Anúncio',
            'news':      'Notícia',
            'lineup':    'Convocatória',
            'highlight': 'Destaque',
        }
        return labels.get(self.post_type, self.post_type)

    @property
    def tagged_team_ids(self):
        return [t.team_id for t in self.tagged_teams]

    def __repr__(self):
        return f'<FeedPost [{self.post_type}] {self.title or self.content[:30]}>'


class FeedPostTeam(db.Model):
    """Equipas marcadas num post — o post aparece no feed privado dessas equipas."""
    __tablename__ = 'feed_post_teams'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('feed_posts.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    team = db.relationship('Team', foreign_keys=[team_id])

    def __repr__(self):
        return f'<FeedPostTeam post={self.post_id} team={self.team_id}>'


class FeedComment(db.Model):
    """Comentário numa publicação do feed."""
    __tablename__ = 'feed_comments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('feed_posts.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('FeedPost', foreign_keys=[post_id],
                           backref=db.backref('comments', lazy=True,
                                              cascade='all, delete-orphan',
                                              order_by='FeedComment.created_at'))
    author = db.relationship('User', foreign_keys=[author_id])

    def __repr__(self):
        return f'<FeedComment post={self.post_id} by={self.author_id}>'
