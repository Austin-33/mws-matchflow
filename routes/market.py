"""
AUSTIN LEAGUE CORE — Mercado Livre de Jogadores
Pedidos de contrato e transferências.
"""
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.user import User, TransferRequest
from models.team import Team, Player

market_bp = Blueprint('market', __name__)

FREE_TEAM_NAME = '__FREE_AGENTS__'


def _get_free_team():
    """Get or create the virtual free agents team."""
    team = Team.query.filter_by(name=FREE_TEAM_NAME).first()
    if not team:
        team = Team(name=FREE_TEAM_NAME, short_name='FREE', sport='futsal',
                    notes='Equipa virtual — jogadores livres')
        db.session.add(team)
        db.session.commit()
    return team


def _is_team_authority(user, team):
    """Check if user has authority to accept/reject requests for a team."""
    if user.role == 'admin':
        return True
    if not user.current_team_id or user.current_team_id != team.id:
        return False
    # Check if user is captain, coach or CEO of the team
    if user.sport_role in ('coach', 'ceo'):
        return True
    # Check if user's player is the captain
    if user.player_id:
        player = Player.query.get(user.player_id)
        if player and team.captain and player.name == team.captain:
            return True
    return False


# ─── Mercado Livre ────────────────────────────────────────────

@market_bp.route('/mercado')
@login_required
def free_market():
    """Lista todos os jogadores livres (sem equipa real)."""
    free_team = Team.query.filter_by(name=FREE_TEAM_NAME).first()

    free_agents = []
    if free_team:
        # Get users linked to players in the free team
        free_agents = User.query.filter(
            User.sport_role.in_(['player', 'coach', 'ceo']),
            User.current_team_id.is_(None),
            User.is_active == True
        ).order_by(User.created_at.desc()).all()

    # My pending requests
    my_requests = []
    if current_user.sport_role in ('player', 'coach', 'ceo'):
        my_requests = TransferRequest.query.filter_by(
            user_id=current_user.id
        ).order_by(TransferRequest.created_at.desc()).limit(10).all()

    # Incoming requests for my team (if I have authority)
    incoming = []
    if current_user.current_team_id:
        team = Team.query.get(current_user.current_team_id)
        if team and _is_team_authority(current_user, team):
            incoming = TransferRequest.query.filter_by(
                team_id=current_user.current_team_id,
                status='pending'
            ).order_by(TransferRequest.created_at.desc()).all()

    teams = Team.query.filter(Team.name != FREE_TEAM_NAME).order_by(Team.name).all()

    return render_template('market/index.html',
                           free_agents=free_agents,
                           my_requests=my_requests,
                           incoming=incoming,
                           teams=teams)


# ─── Enviar pedido de contrato / transferência ────────────────

@market_bp.route('/mercado/request', methods=['POST'])
@login_required
def send_request():
    if current_user.sport_role not in ('player', 'coach', 'ceo'):
        flash('Apenas jogadores, treinadores e CEOs podem enviar pedidos.', 'error')
        return redirect(url_for('market.free_market'))

    team_id = request.form.get('team_id', type=int)
    message = request.form.get('message', '').strip()
    req_type = 'transfer' if current_user.current_team_id else 'contract'

    if not team_id:
        flash('Seleciona uma equipa.', 'error')
        return redirect(url_for('market.free_market'))

    team = Team.query.get_or_404(team_id)
    if team.name == FREE_TEAM_NAME:
        flash('Equipa inválida.', 'error')
        return redirect(url_for('market.free_market'))

    # Check for existing pending request to same team
    existing = TransferRequest.query.filter_by(
        user_id=current_user.id,
        team_id=team_id,
        status='pending'
    ).first()
    if existing:
        flash('Já tens um pedido pendente para esta equipa.', 'error')
        return redirect(url_for('market.free_market'))

    tr = TransferRequest(
        user_id=current_user.id,
        team_id=team_id,
        request_type=req_type,
        message=message,
        created_at=datetime.utcnow(),
    )
    db.session.add(tr)
    db.session.commit()

    type_label = 'transferência' if req_type == 'transfer' else 'contrato'
    flash(f'✅ Pedido de {type_label} enviado para {team.name}!', 'success')
    return redirect(url_for('market.free_market'))


# ─── Cancelar pedido ──────────────────────────────────────────

@market_bp.route('/mercado/request/<int:req_id>/cancel', methods=['POST'])
@login_required
def cancel_request(req_id):
    tr = TransferRequest.query.get_or_404(req_id)
    if tr.user_id != current_user.id:
        flash('Não tens permissão.', 'error')
        return redirect(url_for('market.free_market'))
    if tr.status != 'pending':
        flash('Este pedido já foi processado.', 'error')
        return redirect(url_for('market.free_market'))

    tr.status = 'cancelled'
    db.session.commit()
    flash('Pedido cancelado.', 'info')
    return redirect(url_for('market.free_market'))


# ─── Aceitar pedido ───────────────────────────────────────────

@market_bp.route('/mercado/request/<int:req_id>/accept', methods=['POST'])
@login_required
def accept_request(req_id):
    tr = TransferRequest.query.get_or_404(req_id)
    team = Team.query.get_or_404(tr.team_id)

    if not _is_team_authority(current_user, team):
        flash('Não tens autoridade para aceitar pedidos desta equipa.', 'error')
        return redirect(url_for('market.free_market'))

    if tr.status != 'pending':
        flash('Este pedido já foi processado.', 'error')
        return redirect(url_for('market.free_market'))

    response_msg = request.form.get('response_message', '').strip()
    applicant = User.query.get(tr.user_id)

    # ─── Move player to team ──────────────────────────────────
    free_team = _get_free_team()

    if applicant.player_id:
        player = Player.query.get(applicant.player_id)
        if player:
            # If transfer: remove from old team first
            if tr.request_type == 'transfer' and applicant.current_team_id:
                old_player = Player.query.filter_by(
                    team_id=applicant.current_team_id,
                    id=applicant.player_id
                ).first()
                if old_player:
                    old_player.team_id = free_team.id

            # Move to new team
            player.team_id = team.id
    else:
        # Create player profile if missing
        player = Player(
            name=applicant.full_name or applicant.username,
            position=applicant.preferred_position,
            email=applicant.email,
            status='ativo',
            team_id=team.id,
        )
        db.session.add(player)
        db.session.flush()
        applicant.player_id = player.id

    # Update user's current team
    applicant.current_team_id = team.id

    # Update request
    tr.status = 'accepted'
    tr.response_message = response_msg
    tr.reviewed_by_id = current_user.id
    tr.reviewed_at = datetime.utcnow()

    # Cancel all other pending requests from this user
    TransferRequest.query.filter_by(
        user_id=applicant.id, status='pending'
    ).filter(TransferRequest.id != tr.id).update({'status': 'cancelled'})

    db.session.commit()
    flash(f'✅ {applicant.display_name} aceite na equipa {team.name}!', 'success')
    return redirect(url_for('market.free_market'))


# ─── Recusar pedido ───────────────────────────────────────────

@market_bp.route('/mercado/request/<int:req_id>/reject', methods=['POST'])
@login_required
def reject_request(req_id):
    tr = TransferRequest.query.get_or_404(req_id)
    team = Team.query.get_or_404(tr.team_id)

    if not _is_team_authority(current_user, team):
        flash('Não tens autoridade para recusar pedidos desta equipa.', 'error')
        return redirect(url_for('market.free_market'))

    if tr.status != 'pending':
        flash('Este pedido já foi processado.', 'error')
        return redirect(url_for('market.free_market'))

    tr.status = 'rejected'
    tr.response_message = request.form.get('response_message', '').strip()
    tr.reviewed_by_id = current_user.id
    tr.reviewed_at = datetime.utcnow()
    db.session.commit()

    applicant = User.query.get(tr.user_id)
    flash(f'Pedido de {applicant.display_name} recusado.', 'info')
    return redirect(url_for('market.free_market'))


# ─── Sair da equipa (rescisão) ────────────────────────────────

@market_bp.route('/mercado/leave-team', methods=['POST'])
@login_required
def leave_team():
    if not current_user.current_team_id:
        flash('Não estás em nenhuma equipa.', 'error')
        return redirect(url_for('market.free_market'))

    free_team = _get_free_team()

    if current_user.player_id:
        player = Player.query.get(current_user.player_id)
        if player:
            player.team_id = free_team.id

    current_user.current_team_id = None
    db.session.commit()
    flash('Saíste da equipa. Estás agora no Mercado Livre.', 'info')
    return redirect(url_for('market.free_market'))


# ─── Perfil público de jogador livre ─────────────────────────

@market_bp.route('/mercado/jogador/<int:user_id>')
@login_required
def player_profile(user_id):
    agent = User.query.get_or_404(user_id)
    player = Player.query.get(agent.player_id) if agent.player_id else None
    teams = Team.query.filter(Team.name != FREE_TEAM_NAME).order_by(Team.name).all()

    # Check if current user already sent a request
    existing_request = None
    if current_user.sport_role in ('player', 'coach', 'ceo') and current_user.id == user_id:
        existing_request = TransferRequest.query.filter_by(
            user_id=user_id, status='pending'
        ).first()

    return render_template('market/player_profile.html',
                           agent=agent, player=player, teams=teams,
                           existing_request=existing_request)
