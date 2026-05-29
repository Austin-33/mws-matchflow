import uuid
import secrets
from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    # ─── Identificação ────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False,
                          default=lambda: str(uuid.uuid4()))

    # ─── Credenciais ──────────────────────────────────────────
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False, default='')

    # ─── Perfil ───────────────────────────────────────────────
    full_name = db.Column(db.String(150))
    avatar_url = db.Column(db.String(300), default='')
    role = db.Column(db.String(20), default='manager')
    # sport_role: player | coach | ceo | admin | manager
    sport_role = db.Column(db.String(20), default='player')
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ─── Ligação ao perfil desportivo ─────────────────────────
    # Se sport_role == 'player', este user tem um Player associado
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    # Posição preferida declarada no registo
    preferred_position = db.Column(db.String(50))
    # Equipa atual (preenchida quando aceite numa equipa)
    current_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)

    # ─── Sessão ───────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    last_password_change = db.Column(db.DateTime, nullable=True)

    # ─── Reset de password ────────────────────────────────────
    reset_token = db.Column(db.String(100), nullable=True, unique=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    # ─── Histórico ────────────────────────────────────────────
    password_history = db.relationship(
        'PasswordHistory', backref='user', lazy=True,
        cascade='all, delete-orphan',
        order_by='PasswordHistory.changed_at.desc()'
    )

    # ─── Password ─────────────────────────────────────────────

    def set_password(self, password):
        """
        Hash e guarda a password.
        O histórico é guardado SEPARADAMENTE após commit — chama
        save_password_history() depois de db.session.commit().
        """
        self.password_hash = generate_password_hash(password)
        self.last_password_change = datetime.utcnow()

    def save_password_history(self):
        """
        Guarda o hash atual no histórico.
        Deve ser chamado APÓS db.session.commit() para garantir
        que self.id já existe na base de dados.
        """
        if not self.id or not self.password_hash:
            return

        entry = PasswordHistory(
            user_id=self.id,
            password_hash=self.password_hash
        )
        db.session.add(entry)

        # Manter apenas os últimos 10 registos
        history = PasswordHistory.query.filter_by(user_id=self.id)\
            .order_by(PasswordHistory.changed_at.desc()).all()
        for old in history[10:]:
            db.session.delete(old)

        db.session.commit()

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def was_password_used(self, password):
        """Verifica se a password foi usada nas últimas 5 alterações."""
        recent = PasswordHistory.query.filter_by(user_id=self.id)\
            .order_by(PasswordHistory.changed_at.desc()).limit(5).all()
        return any(check_password_hash(h.password_hash, password) for h in recent)

    # ─── Reset token ──────────────────────────────────────────

    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token

    def verify_reset_token(self, token):
        if not self.reset_token or self.reset_token != token:
            return False
        if not self.reset_token_expires:
            return False
        return datetime.utcnow() < self.reset_token_expires

    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expires = None

    # ─── Helpers ──────────────────────────────────────────────

    @property
    def role_label(self):
        labels = {
            'admin': '👑 Admin',
            'manager': '👔 Manager',
            'player': '⚽ Jogador',
            'coach': '🎽 Treinador',
            'ceo': '👔 CEO',
        }
        return labels.get(self.sport_role or self.role, self.role)

    @property
    def is_free_agent(self):
        """True if user is a player/coach/ceo with no team."""
        return self.sport_role in ('player', 'coach', 'ceo') and not self.current_team_id

    @property
    def display_name(self):
        return self.full_name if self.full_name else self.username

    def record_login(self):
        self.last_login = datetime.utcnow()

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<User {self.username} [{self.public_id}]>'


class PasswordHistory(db.Model):
    __tablename__ = 'password_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PasswordHistory user={self.user_id} at={self.changed_at}>'


class TransferRequest(db.Model):
    """
    Pedido de contrato ou transferência de um utilizador para uma equipa.
    status: pending | accepted | rejected | cancelled
    request_type: contract (jogador livre → equipa) | transfer (jogador com equipa → outra equipa)
    """
    __tablename__ = 'transfer_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    request_type = db.Column(db.String(20), default='contract')  # contract | transfer
    status = db.Column(db.String(20), default='pending')         # pending | accepted | rejected | cancelled
    message = db.Column(db.Text)                                  # mensagem do jogador
    response_message = db.Column(db.Text)                         # resposta da equipa
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='transfer_requests')
    team = db.relationship('Team', foreign_keys=[team_id], backref='transfer_requests')
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])

    @property
    def status_label(self):
        labels = {
            'pending': '⏳ Pendente',
            'accepted': '✅ Aceite',
            'rejected': '❌ Recusado',
            'cancelled': '🚫 Cancelado',
        }
        return labels.get(self.status, self.status)

    @property
    def type_label(self):
        return '📋 Contrato' if self.request_type == 'contract' else '🔄 Transferência'

    def __repr__(self):
        return f'<TransferRequest user={self.user_id} team={self.team_id} [{self.status}]>'
