from datetime import datetime, date, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required

from extensions import db
from models.match import Match, PlayerMatchStat, MatchEvent, MatchLineup
from models.tournament import TournamentTeam, Tournament
from models.team import Player, Team

match_bp = Blueprint('match', __name__)


# ─── List ─────────────────────────────────────────────────────

@match_bp.route('/matches')
@login_required
def list_matches():
    today = datetime.today().strftime('%Y-%m-%d')
    filter_date = request.args.get('date', today)
    filter_status = request.args.get('status', '')

    query = Match.query
    if filter_date:
        query = query.filter_by(date=filter_date)
    if filter_status:
        query = query.filter_by(status=filter_status)

    matches = query.order_by(Match.date, Match.time).all()
    return render_template('match/list.html', matches=matches,
                           filter_date=filter_date, filter_status=filter_status, today=today)


# ─── Detail ───────────────────────────────────────────────────

@match_bp.route('/matches/<int:match_id>')
@login_required
def match_detail(match_id):
    match = Match.query.get_or_404(match_id)
    team1_players = Player.query.filter_by(team_id=match.team1_id, status='ativo').order_by(Player.number).all()
    team2_players = Player.query.filter_by(team_id=match.team2_id, status='ativo').order_by(Player.number).all()
    stats = PlayerMatchStat.query.filter_by(match_id=match_id).all()
    events = MatchEvent.query.filter_by(match_id=match_id).order_by(MatchEvent.minute).all()

    lineup1 = MatchLineup.query.filter_by(match_id=match_id, team_id=match.team1_id).all()
    lineup2 = MatchLineup.query.filter_by(match_id=match_id, team_id=match.team2_id).all()

    return render_template('match/detail.html', match=match,
                           team1_players=team1_players, team2_players=team2_players,
                           stats=stats, events=events,
                           lineup1=lineup1, lineup2=lineup2)


# ─── Match Play (live control panel) ─────────────────────────

@match_bp.route('/matches/<int:match_id>/play')
@login_required
def match_play(match_id):
    match = Match.query.get_or_404(match_id)
    team1_players = Player.query.filter_by(team_id=match.team1_id).order_by(Player.number).all()
    team2_players = Player.query.filter_by(team_id=match.team2_id).order_by(Player.number).all()
    events = MatchEvent.query.filter_by(match_id=match_id).order_by(MatchEvent.minute).all()
    lineup1 = MatchLineup.query.filter_by(match_id=match_id, team_id=match.team1_id).all()
    lineup2 = MatchLineup.query.filter_by(match_id=match_id, team_id=match.team2_id).all()

    return render_template('match/play.html', match=match,
                           team1_players=team1_players, team2_players=team2_players,
                           events=events, lineup1=lineup1, lineup2=lineup2)


# ─── Start / End match ────────────────────────────────────────

@match_bp.route('/matches/<int:match_id>/start', methods=['POST'])
@login_required
def start_match(match_id):
    match = Match.query.get_or_404(match_id)
    match.status = 'live'
    match.score1 = 0
    match.score2 = 0
    db.session.commit()
    return redirect(url_for('match.match_play', match_id=match_id))


@match_bp.route('/matches/<int:match_id>/end', methods=['POST'])
@login_required
def end_match(match_id):
    match = Match.query.get_or_404(match_id)
    match.status = 'finished'
    _update_standings(match)
    db.session.commit()
    # ─── Auto-post resultado no feed ──────────────────────────
    from utils.feed_helpers import create_match_result_post
    create_match_result_post(match)
    flash('Jogo terminado! Resultado publicado no feed. ✅', 'success')
    return redirect(url_for('match.match_detail', match_id=match_id))


# ─── Add event (AJAX) ─────────────────────────────────────────

@match_bp.route('/matches/<int:match_id>/event', methods=['POST'])
@login_required
def add_event(match_id):
    match = Match.query.get_or_404(match_id)
    data = request.get_json() or request.form

    event_type = data.get('event_type', '')
    minute = int(data.get('minute', 0))
    team_id = data.get('team_id', type=int) if hasattr(data, 'get') else int(data.get('team_id', 0) or 0)
    player_id = int(data.get('player_id') or 0) or None
    player2_id = int(data.get('player2_id') or 0) or None
    description = data.get('description', '')

    event = MatchEvent(
        match_id=match_id,
        minute=minute,
        event_type=event_type,
        team_id=team_id,
        player_id=player_id,
        player2_id=player2_id,
        description=description,
        created_at=datetime.utcnow(),
    )
    db.session.add(event)

    # Update score for goals
    if event_type in ('goal', 'penalty'):
        if team_id == match.team1_id:
            match.score1 = (match.score1 or 0) + 1
        elif team_id == match.team2_id:
            match.score2 = (match.score2 or 0) + 1
    elif event_type == 'own_goal':
        if team_id == match.team1_id:
            match.score2 = (match.score2 or 0) + 1
        elif team_id == match.team2_id:
            match.score1 = (match.score1 or 0) + 1

    # Update player stats for cards
    if player_id:
        player = Player.query.get(player_id)
        if player:
            if event_type in ('yellow_card', 'foul_yellow'):
                player.yellow_cards = (player.yellow_cards or 0) + 1
            elif event_type in ('red_card', 'foul_red'):
                player.red_cards = (player.red_cards or 0) + 1
            elif event_type in ('goal', 'penalty'):
                player.goals = (player.goals or 0) + 1
            if player2_id and event_type == 'goal':
                p2 = Player.query.get(player2_id)
                if p2:
                    p2.assists = (p2.assists or 0) + 1

    db.session.commit()

    return jsonify({
        'ok': True,
        'score1': match.score1,
        'score2': match.score2,
        'event': {
            'id': event.id,
            'minute': event.minute,
            'type': event.event_type,
            'icon': event.icon,
            'description': event.description,
        }
    })


# ─── Delete event ─────────────────────────────────────────────

@match_bp.route('/matches/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = MatchEvent.query.get_or_404(event_id)
    match = event.match

    # Reverse score
    if event.event_type in ('goal', 'penalty'):
        if event.team_id == match.team1_id:
            match.score1 = max(0, (match.score1 or 0) - 1)
        elif event.team_id == match.team2_id:
            match.score2 = max(0, (match.score2 or 0) - 1)
    elif event.event_type == 'own_goal':
        if event.team_id == match.team1_id:
            match.score2 = max(0, (match.score2 or 0) - 1)
        elif event.team_id == match.team2_id:
            match.score1 = max(0, (match.score1 or 0) - 1)

    db.session.delete(event)
    db.session.commit()
    return jsonify({'ok': True, 'score1': match.score1, 'score2': match.score2})


# ─── Save lineup ──────────────────────────────────────────────

@match_bp.route('/matches/<int:match_id>/lineup', methods=['POST'])
@login_required
def save_lineup(match_id):
    match = Match.query.get_or_404(match_id)
    team_id = request.form.get('team_id', type=int)
    formation = request.form.get('formation', '')

    # Clear existing lineup for this team
    MatchLineup.query.filter_by(match_id=match_id, team_id=team_id).delete()

    starter_ids = request.form.getlist('starters')
    sub_ids = request.form.getlist('subs')

    for pid in starter_ids:
        if pid:
            p = Player.query.get(int(pid))
            db.session.add(MatchLineup(
                match_id=match_id, team_id=team_id, player_id=int(pid),
                is_starter=True, formation=formation,
                shirt_number=p.number if p else None,
                position_override=p.position if p else None,
            ))

    for pid in sub_ids:
        if pid:
            p = Player.query.get(int(pid))
            db.session.add(MatchLineup(
                match_id=match_id, team_id=team_id, player_id=int(pid),
                is_starter=False, formation=formation,
                shirt_number=p.number if p else None,
            ))

    db.session.commit()
    flash('Onze guardado! ✅', 'success')
    return redirect(url_for('match.match_play', match_id=match_id))


# ─── Result (manual) ──────────────────────────────────────────

@match_bp.route('/matches/<int:match_id>/result', methods=['POST'])
@login_required
def update_result(match_id):
    match = Match.query.get_or_404(match_id)
    score1 = request.form.get('score1', type=int)
    score2 = request.form.get('score2', type=int)

    if score1 is None or score2 is None:
        flash('Introduz os dois resultados.', 'error')
        return redirect(url_for('match.match_detail', match_id=match_id))

    match.score1 = score1
    match.score2 = score2
    match.status = 'finished'
    _update_standings(match)
    db.session.commit()
    # ─── Auto-post resultado no feed ──────────────────────────
    from utils.feed_helpers import create_match_result_post
    create_match_result_post(match)
    flash('Resultado registado e publicado no feed! 🏆', 'success')
    return redirect(url_for('match.match_detail', match_id=match_id))


# ─── Player stats ─────────────────────────────────────────────

@match_bp.route('/matches/<int:match_id>/stats', methods=['POST'])
@login_required
def update_player_stats(match_id):
    match = Match.query.get_or_404(match_id)
    player_ids = request.form.getlist('player_id')

    for pid in player_ids:
        pid = int(pid)
        stat = PlayerMatchStat.query.filter_by(match_id=match_id, player_id=pid).first()
        if not stat:
            stat = PlayerMatchStat(match_id=match_id, player_id=pid)
            db.session.add(stat)

        stat.goals = int(request.form.get(f'goals_{pid}', 0))
        stat.assists = int(request.form.get(f'assists_{pid}', 0))
        stat.yellow_cards = int(request.form.get(f'yellow_{pid}', 0))
        stat.red_cards = int(request.form.get(f'red_{pid}', 0))
        stat.minutes_played = int(request.form.get(f'minutes_{pid}', 40))

        player = Player.query.get(pid)
        if player:
            player.goals = db.session.query(db.func.sum(PlayerMatchStat.goals)).filter_by(player_id=pid).scalar() or 0
            player.assists = db.session.query(db.func.sum(PlayerMatchStat.assists)).filter_by(player_id=pid).scalar() or 0
            player.yellow_cards = db.session.query(db.func.sum(PlayerMatchStat.yellow_cards)).filter_by(player_id=pid).scalar() or 0
            player.red_cards = db.session.query(db.func.sum(PlayerMatchStat.red_cards)).filter_by(player_id=pid).scalar() or 0
            player.matches_played = PlayerMatchStat.query.filter_by(player_id=pid).count()

    db.session.commit()
    flash('Estatísticas atualizadas!', 'success')
    return redirect(url_for('match.match_detail', match_id=match_id))


# ─── Standings helper ─────────────────────────────────────────

def _update_standings(match):
    t1 = TournamentTeam.query.filter_by(tournament_id=match.tournament_id, team_id=match.team1_id).first()
    t2 = TournamentTeam.query.filter_by(tournament_id=match.tournament_id, team_id=match.team2_id).first()
    if not t1 or not t2:
        return
    t1.played += 1; t2.played += 1
    t1.goals_for += match.score1; t1.goals_against += match.score2
    t2.goals_for += match.score2; t2.goals_against += match.score1
    if match.score1 > match.score2:
        t1.wins += 1; t1.points += 3; t2.losses += 1
    elif match.score1 < match.score2:
        t2.wins += 1; t2.points += 3; t1.losses += 1
    else:
        t1.draws += 1; t2.draws += 1; t1.points += 1; t2.points += 1


# ─── Calendário de Jogos ──────────────────────────────────────

@match_bp.route('/calendario')
@login_required
def calendario():
    """
    Calendário mensal de jogos.
    Parâmetros: year, month, tournament_id (opcional)
    Ao clicar numa data → lista os jogos desse dia.
    """
    today = date.today()
    year  = request.args.get('year',  type=int, default=today.year)
    month = request.args.get('month', type=int, default=today.month)
    selected_date = request.args.get('date', '')          # YYYY-MM-DD
    tournament_id = request.args.get('tournament_id', type=int)

    # Navegar entre meses
    if month < 1:  month = 12; year -= 1
    if month > 12: month = 1;  year += 1

    # Primeiro e último dia do mês
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    # Todos os jogos do mês
    first_str = first_day.strftime('%Y-%m-%d')
    last_str  = last_day.strftime('%Y-%m-%d')

    query = Match.query.filter(
        Match.date >= first_str,
        Match.date <= last_str
    )
    if tournament_id:
        query = query.filter_by(tournament_id=tournament_id)

    month_matches = query.order_by(Match.date, Match.time).all()

    # Agrupar por data → {date_str: [matches]}
    matches_by_date = {}
    for m in month_matches:
        if m.date:
            matches_by_date.setdefault(m.date, []).append(m)

    # Jogos do dia selecionado (ou hoje se nenhum selecionado)
    day_matches = []
    if selected_date:
        day_matches = matches_by_date.get(selected_date, [])
    elif today.strftime('%Y-%m-%d') in matches_by_date:
        selected_date = today.strftime('%Y-%m-%d')
        day_matches = matches_by_date[selected_date]

    # Construir grelha do calendário (semanas)
    # Começa na segunda-feira da semana do primeiro dia
    start = first_day - timedelta(days=first_day.weekday())  # Monday
    weeks = []
    current = start
    while current <= last_day or len(weeks) < 6:
        week = []
        for _ in range(7):
            week.append(current)
            current += timedelta(days=1)
        weeks.append(week)
        if current > last_day and len(weeks) >= 4:
            break

    # Todos os torneios para o filtro
    tournaments = Tournament.query.order_by(Tournament.name).all()

    # Meses para navegação
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year if month < 12 else year + 1

    month_names = [
        '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]

    return render_template('match/calendario.html',
                           year=year, month=month,
                           month_name=month_names[month],
                           weeks=weeks,
                           first_day=first_day,
                           last_day=last_day,
                           today=today,
                           matches_by_date=matches_by_date,
                           selected_date=selected_date,
                           day_matches=day_matches,
                           tournaments=tournaments,
                           tournament_id=tournament_id,
                           prev_month=prev_month, prev_year=prev_year,
                           next_month=next_month, next_year=next_year)


# ─── API: jogos de um dia (AJAX) ──────────────────────────────

@match_bp.route('/calendario/dia')
@login_required
def calendario_dia():
    """Retorna os jogos de uma data específica em JSON para AJAX."""
    day = request.args.get('date', '')
    tournament_id = request.args.get('tournament_id', type=int)

    if not day:
        return jsonify([])

    query = Match.query.filter_by(date=day)
    if tournament_id:
        query = query.filter_by(tournament_id=tournament_id)

    matches = query.order_by(Match.time).all()

    return jsonify([{
        'id': m.id,
        'team1': m.team1.name,
        'team2': m.team2.name,
        'team1_logo': m.team1.logo_url or '',
        'team2_logo': m.team2.logo_url or '',
        'score': m.score_display,
        'status': m.status,
        'time': m.time or '',
        'tournament': m.tournament.name,
        'phase': m.phase_label,
        'url': url_for('match.match_detail', match_id=m.id),
        'play_url': url_for('match.match_play', match_id=m.id),
    } for m in matches])
