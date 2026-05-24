"""AUSTIN LEAGUE CORE — Finance & Awards Routes."""
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.tournament import Tournament, TournamentTeam
from models.finance import TournamentAward, TeamPayment
from models.team import Player, Team
from models.match import PlayerMatchStat

finance_bp = Blueprint('finance', __name__)


# ─── Finance & Awards page ────────────────────────────────────

@finance_bp.route('/tournaments/<int:tid>/finance', methods=['GET', 'POST'])
@login_required
def finance(tid):
    tournament = Tournament.query.get_or_404(tid)
    registered = TournamentTeam.query.filter_by(tournament_id=tid).all()
    awards = TournamentAward.query.filter_by(tournament_id=tid).order_by(TournamentAward.id).all()
    payments = TeamPayment.query.filter_by(tournament_id=tid).order_by(TeamPayment.team_id).all()

    # Auto-calculate stats for player awards
    stats = _calc_stats(tid)

    # Financial summary
    total_reg   = sum(p.amount for p in payments if p.payment_type == 'registration' and p.status == 'paid')
    total_part  = sum(p.amount for p in payments if p.payment_type == 'participation' and p.status == 'paid')
    total_collected = total_reg + total_part
    total_prizes = sum(a.prize_value for a in awards if a.is_active)

    return render_template('tournament/finance.html',
                           tournament=tournament,
                           registered=registered,
                           awards=awards,
                           payments=payments,
                           stats=stats,
                           total_collected=total_collected,
                           total_prizes=total_prizes,
                           balance=total_collected - total_prizes)


# ─── Save finance settings ────────────────────────────────────

@finance_bp.route('/tournaments/<int:tid>/finance/settings', methods=['POST'])
@login_required
def save_settings(tid):
    tournament = Tournament.query.get_or_404(tid)
    tournament.currency          = request.form.get('currency', 'KWZ').strip()
    tournament.registration_fee  = float(request.form.get('registration_fee', 0) or 0)
    tournament.participation_fee = float(request.form.get('participation_fee', 0) or 0)
    tournament.prize_pool_total  = float(request.form.get('prize_pool_total', 0) or 0)
    db.session.commit()

    # Auto-create payment records for all registered teams
    registered = TournamentTeam.query.filter_by(tournament_id=tid).all()
    for tt in registered:
        for ptype, amount in [('registration', tournament.registration_fee),
                               ('participation', tournament.participation_fee)]:
            if amount > 0:
                existing = TeamPayment.query.filter_by(
                    tournament_id=tid, team_id=tt.team_id, payment_type=ptype
                ).first()
                if not existing:
                    db.session.add(TeamPayment(
                        tournament_id=tid,
                        team_id=tt.team_id,
                        payment_type=ptype,
                        amount=amount,
                        currency=tournament.currency,
                        status='pending',
                        created_at=datetime.utcnow(),
                    ))
    db.session.commit()
    flash('✅ Configurações financeiras guardadas!', 'success')
    return redirect(url_for('finance.finance', tid=tid))


# ─── Update payment status ────────────────────────────────────

@finance_bp.route('/tournaments/<int:tid>/finance/payment/<int:pid>', methods=['POST'])
@login_required
def update_payment(tid, pid):
    payment = TeamPayment.query.get_or_404(pid)
    new_status = request.form.get('status', 'pending')
    payment.status = new_status
    if new_status == 'paid':
        payment.paid_at = datetime.utcnow()
    payment.notes = request.form.get('notes', payment.notes or '').strip()
    db.session.commit()
    return jsonify({'ok': True, 'status': payment.status_label})


# ─── Save awards config ───────────────────────────────────────

@finance_bp.route('/tournaments/<int:tid>/finance/awards', methods=['POST'])
@login_required
def save_awards(tid):
    tournament = Tournament.query.get_or_404(tid)

    # Delete existing awards and recreate
    TournamentAward.query.filter_by(tournament_id=tid).delete()

    award_types = request.form.getlist('award_type')
    labels      = request.form.getlist('award_label')
    values      = request.form.getlist('award_value')
    descs       = request.form.getlist('award_desc')
    actives     = request.form.getlist('award_active')  # checkboxes — only checked ones sent

    for i, atype in enumerate(award_types):
        if not atype:
            continue
        is_active = str(i) in actives
        db.session.add(TournamentAward(
            tournament_id=tid,
            award_type=atype,
            label=labels[i] if i < len(labels) else '',
            prize_value=float(values[i] if i < len(values) else 0 or 0),
            prize_desc=descs[i] if i < len(descs) else '',
            is_active=is_active,
            created_at=datetime.utcnow(),
        ))

    db.session.commit()
    flash('✅ Premiações guardadas!', 'success')
    return redirect(url_for('finance.finance', tid=tid))


# ─── Assign award winners ─────────────────────────────────────

@finance_bp.route('/tournaments/<int:tid>/finance/awards/assign', methods=['POST'])
@login_required
def assign_winners(tid):
    """Auto-assign winners based on stats, or manual override."""
    stats = _calc_stats(tid)

    awards = TournamentAward.query.filter_by(tournament_id=tid, is_active=True).all()
    for award in awards:
        if award.award_type == 'top_scorer' and stats.get('top_scorer'):
            award.winner_player_id = stats['top_scorer'].id
        elif award.award_type == 'top_assist' and stats.get('top_assist'):
            award.winner_player_id = stats['top_assist'].id
        elif award.award_type == 'mvp' and stats.get('mvp'):
            award.winner_player_id = stats['mvp'].id
        elif award.award_type == 'best_gk' and stats.get('best_gk'):
            award.winner_player_id = stats['best_gk'].id
        elif award.award_type == '1st' and stats.get('1st'):
            award.winner_team_id = stats['1st'].team_id
        elif award.award_type == '2nd' and stats.get('2nd'):
            award.winner_team_id = stats['2nd'].team_id
        elif award.award_type == '3rd' and stats.get('3rd'):
            award.winner_team_id = stats['3rd'].team_id

    db.session.commit()
    flash('✅ Vencedores atribuídos automaticamente!', 'success')
    return redirect(url_for('finance.finance', tid=tid))


# ─── Stats calculator ─────────────────────────────────────────

def _calc_stats(tid):
    """Calculate all award stats for a tournament."""
    from models.tournament import TournamentTeam

    # Standings (for 1st/2nd/3rd)
    standings = TournamentTeam.query.filter_by(tournament_id=tid).order_by(
        TournamentTeam.points.desc(),
        TournamentTeam.goals_for.desc()
    ).all()

    # Players in this tournament
    team_ids = [tt.team_id for tt in standings]
    players = Player.query.filter(Player.team_id.in_(team_ids)).all() if team_ids else []

    # Top scorer
    top_scorer = sorted(players, key=lambda p: p.goals or 0, reverse=True)
    top_scorer = top_scorer[0] if top_scorer and top_scorer[0].goals else None

    # Top assist
    top_assist = sorted(players, key=lambda p: p.assists or 0, reverse=True)
    top_assist = top_assist[0] if top_assist and top_assist[0].assists else None

    # MVP — weighted score: goals×3 + assists×2 + matches×1 - yellow×0.5 - red×2
    def mvp_score(p):
        return (p.goals or 0)*3 + (p.assists or 0)*2 + (p.matches_played or 0) - (p.yellow_cards or 0)*0.5 - (p.red_cards or 0)*2

    mvp_list = sorted(players, key=mvp_score, reverse=True)
    mvp = mvp_list[0] if mvp_list else None

    # Best GK — players with position GR, fewest goals conceded (via team standings)
    gk_players = [p for p in players if p.position and 'GR' in p.position.upper()]
    best_gk = None
    if gk_players:
        # GK from team with best goals_against ratio
        gk_teams = {tt.team_id: tt for tt in standings}
        best_gk = min(gk_players, key=lambda p: gk_teams.get(p.team_id, TournamentTeam()).goals_against or 999)

    return {
        '1st':        standings[0] if len(standings) > 0 else None,
        '2nd':        standings[1] if len(standings) > 1 else None,
        '3rd':        standings[2] if len(standings) > 2 else None,
        'top_scorer': top_scorer,
        'top_assist': top_assist,
        'mvp':        mvp,
        'best_gk':    best_gk,
        'standings':  standings,
        'players':    players,
        'mvp_score':  mvp_score,
    }
