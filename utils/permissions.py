"""
AUSTIN LEAGUE CORE — Permissões Centralizadas
==============================================
Hierarquia de roles:
  admin   → acesso total
  manager → gere equipas e campeonatos (atribuído pelo admin)
  player  → só leitura + mercado livre

Regra de ownership:
  - Só o criador do torneio/jogo OU um admin pode editar/apagar.
  - Um manager pode criar, mas só edita/apaga o que criou.
"""
from functools import wraps
from flask import flash, redirect, url_for, jsonify, request
from flask_login import current_user


# ── Helpers básicos ───────────────────────────────────────────

def is_admin():
    return current_user.is_authenticated and current_user.role == 'admin'

def is_manager():
    return current_user.is_authenticated and current_user.role in ('admin', 'manager')

def is_player_only():
    return current_user.is_authenticated and current_user.role == 'player'


# ── Ownership ─────────────────────────────────────────────────

def can_edit_tournament(tournament):
    """
    Pode editar/apagar este torneio?
    - admin: sempre
    - manager: só se for o criador
    """
    if not current_user.is_authenticated:
        return False
    if current_user.role == 'admin':
        return True
    if current_user.role == 'manager':
        # Se o torneio não tem criador registado, qualquer manager pode editar
        if tournament.created_by_id is None:
            return True
        return tournament.created_by_id == current_user.id
    return False


def can_edit_match(match):
    """
    Pode editar/apagar/reiniciar este jogo?
    - admin: sempre
    - manager: só se for o criador do torneio ou do jogo
    """
    if not current_user.is_authenticated:
        return False
    if current_user.role == 'admin':
        return True
    if current_user.role == 'manager':
        # Criador do jogo
        if match.created_by_id and match.created_by_id == current_user.id:
            return True
        # Criador do torneio ao qual o jogo pertence
        if match.tournament and match.tournament.created_by_id == current_user.id:
            return True
        # Torneio sem criador registado → qualquer manager
        if match.tournament and match.tournament.created_by_id is None:
            return True
    return False


def can_manage_team(team_id=None):
    """Pode gerir equipas? Qualquer manager/admin."""
    return current_user.is_authenticated and current_user.role in ('admin', 'manager')


# ── Decoradores ───────────────────────────────────────────────

def _is_ajax():
    return request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def require_manager(f):
    """Exige role manager ou admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role not in ('admin', 'manager'):
            if _is_ajax():
                return jsonify({'ok': False, 'error': 'Sem permissão'}), 403
            flash('🔒 Acesso restrito. Precisas de permissão de gestor.', 'error')
            return redirect(request.referrer or url_for('index'))
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Exige role admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            if _is_ajax():
                return jsonify({'ok': False, 'error': 'Acesso restrito a administradores'}), 403
            flash('🔒 Acesso restrito a administradores.', 'error')
            return redirect(request.referrer or url_for('index'))
        return f(*args, **kwargs)
    return decorated


def require_tournament_owner(f):
    """
    Exige que o utilizador seja admin OU criador do torneio.
    Usa o argumento 'tournament_id' da rota.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role not in ('admin', 'manager'):
            if _is_ajax():
                return jsonify({'ok': False, 'error': 'Sem permissão'}), 403
            flash('🔒 Sem permissão.', 'error')
            return redirect(request.referrer or url_for('index'))

        # Verificar ownership
        from models.tournament import Tournament
        tid = kwargs.get('tournament_id') or kwargs.get('tid')
        if tid:
            t = Tournament.query.get(tid)
            if t and not can_edit_tournament(t):
                if _is_ajax():
                    return jsonify({'ok': False, 'error': 'Só o criador pode editar este torneio'}), 403
                flash('🔒 Só o criador do torneio pode fazer esta alteração.', 'error')
                return redirect(request.referrer or url_for('tournament.tournament_room', tournament_id=tid))

        return f(*args, **kwargs)
    return decorated


def require_match_owner(f):
    """
    Exige que o utilizador seja admin OU criador do torneio/jogo.
    Usa o argumento 'match_id' da rota.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role not in ('admin', 'manager'):
            if _is_ajax():
                return jsonify({'ok': False, 'error': 'Sem permissão'}), 403
            flash('🔒 Sem permissão.', 'error')
            return redirect(request.referrer or url_for('index'))

        from models.match import Match
        mid = kwargs.get('match_id') or kwargs.get('event_id')
        if mid:
            # Para event_id, buscar o match via evento
            if 'event_id' in kwargs:
                from models.match import MatchEvent
                ev = MatchEvent.query.get(mid)
                match = ev.match if ev else None
            else:
                match = Match.query.get(mid)

            if match and not can_edit_match(match):
                if _is_ajax():
                    return jsonify({'ok': False, 'error': 'Só o criador pode editar este jogo'}), 403
                flash('🔒 Só o criador do torneio pode alterar este jogo.', 'error')
                return redirect(request.referrer or url_for('index'))

        return f(*args, **kwargs)
    return decorated
