import os, random, string
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user

from extensions import db
from models.tournament import Tournament, Group, TournamentTeam
from models.team import Team
from models.match import Match
from utils.scheduler import generate_round_robin, assign_dates, generate_groups, generate_knockout_bracket, auto_knockout_structure
from utils.permissions import require_manager, require_tournament_owner, require_match_owner, can_edit_tournament

tournament_bp = Blueprint('tournament', __name__)


# ─── List ─────────────────────────────────────────────────────

@tournament_bp.route('/tournaments')
@login_required
def list_tournaments():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template('tournament/list.html', tournaments=tournaments)


# ─── Create ───────────────────────────────────────────────────

@tournament_bp.route('/tournaments/create', methods=['GET', 'POST'])
@login_required
@require_manager
def create_tournament():
    teams = Team.query.order_by(Team.name).all()

    if request.method == 'POST':
        f = request.form
        name = f.get('name', '').strip()
        sport = f.get('sport', 'futsal')
        t_type = f.get('type', 'liga')
        format_type = f.get('format_type', 'liga')
        start_date = f.get('start_date', '')
        description = f.get('description', '').strip()
        selected_ids = f.getlist('team_ids')
        open_registration = 'open_registration' in f

        has_groups = 'has_groups' in f
        groups_count = int(f.get('groups_count') or 2)
        teams_per_group = int(f.get('teams_per_group') or 4)
        qualify_per_group = int(f.get('qualify_per_group') or 2)
        group_legs = int(f.get('group_legs') or 1)

        has_knockout = 'has_knockout' in f
        auto_phases = 'auto_phases' in f
        has_round_of_16 = 'has_round_of_16' in f
        has_quarter = 'has_quarter' in f
        has_semi = 'has_semi' in f
        has_final = 'has_final' in f
        knockout_legs = int(f.get('knockout_legs') or 1)
        teams_count = int(f.get('teams_count') or 0)

        if not name or not start_date:
            flash('Preenche o nome e a data de início.', 'error')
            return render_template('tournament/create.html', teams=teams)

        if auto_phases and has_knockout:
            qualifier_count = qualify_per_group * groups_count if has_groups else teams_count
            phases = auto_knockout_structure(qualifier_count)
            has_round_of_16 = any(p[0] == 'round_of_16' for p in phases)
            has_quarter = any(p[0] == 'quarter' for p in phases)
            has_semi = any(p[0] == 'semi' for p in phases)
            has_final = True

        # Status: pending if open for registration, active if teams already selected
        status = 'pending' if open_registration else 'active'

        tournament = Tournament(
            name=name, sport=sport, type=t_type, status=status,
            format_type=format_type,
            teams_count=teams_count, description=description,
            has_groups=has_groups, groups_count=groups_count,
            teams_per_group=teams_per_group, qualify_per_group=qualify_per_group,
            group_legs=group_legs, has_knockout=has_knockout,
            has_round_of_16=has_round_of_16, has_quarter=has_quarter,
            has_semi=has_semi, has_final=has_final, knockout_legs=knockout_legs,
            start_date=start_date,
            created_by_id=current_user.id,
        )
        db.session.add(tournament)
        db.session.commit()

        # Handle logo upload
        if 'logo' in request.files:
            f_logo = request.files['logo']
            if f_logo and f_logo.filename:
                from austinapp import allowed_file
                import uuid
                if allowed_file(f_logo.filename):
                    ext = f_logo.filename.rsplit('.', 1)[1].lower()
                    fname = f'tournament_{tournament.id}_{uuid.uuid4().hex[:8]}.{ext}'
                    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'logos', fname)
                    f_logo.save(save_path)
                    tournament.logo_url = f'uploads/logos/{fname}'
                    db.session.commit()

        if not open_registration and selected_ids:
            selected_teams = Team.query.filter(Team.id.in_(selected_ids)).all()
            team_id_list = [t.id for t in selected_teams]
            tournament.teams_count = len(team_id_list)

            if t_type == 'liga':
                _setup_league(tournament, team_id_list, start_date, group_legs)
            elif t_type == 'grupos_eliminatoria':
                _setup_groups_knockout(tournament, team_id_list, groups_count, qualify_per_group, start_date, group_legs)
            elif t_type == 'eliminatoria':
                _setup_pure_knockout(tournament, team_id_list, start_date)

            db.session.commit()
            flash(f'🚀 Torneio "{name}" criado! Calendário gerado.', 'success')
        else:
            flash(f'🏆 Torneio "{name}" criado! Inscrições abertas.', 'success')

        return redirect(url_for('tournament.tournament_room', tournament_id=tournament.id))

    return render_template('tournament/create.html', teams=teams)


# ─── Register team (open registration) ───────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/register', methods=['POST'])
@login_required
@require_tournament_owner
def register_team(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    team_id = request.form.get('team_id', type=int)

    if not team_id:
        flash('Seleciona uma equipa.', 'error')
        return redirect(url_for('tournament.tournament_room', tournament_id=tournament_id))

    existing = TournamentTeam.query.filter_by(tournament_id=tournament_id, team_id=team_id).first()
    if existing:
        flash('Esta equipa já está inscrita.', 'error')
        return redirect(url_for('tournament.tournament_room', tournament_id=tournament_id))

    if tournament.teams_count and tournament.registered_teams_count >= tournament.teams_count:
        flash('Torneio já atingiu o número máximo de equipas.', 'error')
        return redirect(url_for('tournament.tournament_room', tournament_id=tournament_id))

    tt = TournamentTeam(tournament_id=tournament_id, team_id=team_id)
    db.session.add(tt)
    db.session.commit()
    flash('Equipa inscrita com sucesso! ✅', 'success')
    return redirect(url_for('tournament.tournament_room', tournament_id=tournament_id))


# ─── Generate calendar (after registration closes) ────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/generate', methods=['POST'])
@login_required
@require_tournament_owner
def generate_calendar(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    team_ids = [tt.team_id for tt in TournamentTeam.query.filter_by(tournament_id=tournament_id).all()]

    if len(team_ids) < 2:
        flash('Precisas de pelo menos 2 equipas para gerar o calendário.', 'error')
        return redirect(url_for('tournament.tournament_room', tournament_id=tournament_id))

    # Delete existing matches
    Match.query.filter_by(tournament_id=tournament_id).delete()
    Group.query.filter_by(tournament_id=tournament_id).delete()
    db.session.commit()

    start_date = tournament.start_date or datetime.today().strftime('%Y-%m-%d')

    if tournament.type == 'liga':
        _setup_league(tournament, team_ids, start_date, tournament.group_legs or 1)
    elif tournament.type == 'grupos_eliminatoria':
        _setup_groups_knockout(tournament, team_ids, tournament.groups_count or 2,
                               tournament.qualify_per_group or 2, start_date, tournament.group_legs or 1)
    elif tournament.type == 'eliminatoria':
        _setup_pure_knockout(tournament, team_ids, start_date)

    tournament.status = 'active'
    db.session.commit()
    flash('📅 Calendário gerado com sucesso!', 'success')
    return redirect(url_for('tournament.tournament_room', tournament_id=tournament_id))


# ─── Assign groups manually ───────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/assign-groups', methods=['POST'])
@login_required
@require_tournament_owner
def assign_groups(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    mode = request.form.get('mode', 'random')  # random | manual

    registered = TournamentTeam.query.filter_by(tournament_id=tournament_id).all()
    team_ids = [tt.team_id for tt in registered]

    # Clear existing group assignments
    Group.query.filter_by(tournament_id=tournament_id).delete()
    for tt in registered:
        tt.group_id = None
        tt.group_letter = None
    db.session.flush()

    num_groups = tournament.groups_count or 2

    if mode == 'random':
        groups_dict = generate_groups(team_ids, num_groups)
    else:
        # Manual: read from form group_A[], group_B[], etc.
        groups_dict = {}
        for letter in string.ascii_uppercase[:num_groups]:
            ids = request.form.getlist(f'group_{letter}[]')
            groups_dict[letter] = [int(i) for i in ids if i]

    for letter, g_team_ids in groups_dict.items():
        grp = Group(name=letter, tournament_id=tournament_id)
        db.session.add(grp)
        db.session.flush()
        for tid in g_team_ids:
            tt = TournamentTeam.query.filter_by(tournament_id=tournament_id, team_id=tid).first()
            if tt:
                tt.group_id = grp.id
                tt.group_letter = letter

    db.session.commit()
    flash('Grupos definidos! ✅', 'success')
    return redirect(url_for('tournament.tournament_room', tournament_id=tournament_id))


# ─── Setup helpers ────────────────────────────────────────────

def _setup_league(tournament, team_ids, start_date, legs=1):
    for tid in team_ids:
        if not TournamentTeam.query.filter_by(tournament_id=tournament.id, team_id=tid).first():
            db.session.add(TournamentTeam(tournament_id=tournament.id, team_id=tid))

    schedule = generate_round_robin(team_ids)
    if legs == 2:
        # Add reverse fixtures
        reverse = [[(b, a) for a, b in rnd] for rnd in schedule]
        schedule = schedule + reverse

    dated = assign_dates(schedule, start_date)
    for m in dated:
        db.session.add(Match(
            tournament_id=tournament.id, team1_id=m['team1'], team2_id=m['team2'],
            date=m['date'], round_number=m['round_number'], phase='group',
        ))


def _setup_groups_knockout(tournament, team_ids, num_groups, qualify_per_group, start_date, legs=1):
    groups_dict = generate_groups(team_ids, num_groups)

    for letter, g_ids in groups_dict.items():
        grp = Group(name=letter, tournament_id=tournament.id)
        db.session.add(grp)
        db.session.flush()

        for tid in g_ids:
            if not TournamentTeam.query.filter_by(tournament_id=tournament.id, team_id=tid).first():
                db.session.add(TournamentTeam(
                    tournament_id=tournament.id, team_id=tid,
                    group_id=grp.id, group_letter=letter,
                ))

        schedule = generate_round_robin(g_ids)
        if legs == 2:
            reverse = [[(b, a) for a, b in rnd] for rnd in schedule]
            schedule = schedule + reverse

        dated = assign_dates(schedule, start_date, days_between=7)
        for m in dated:
            db.session.add(Match(
                tournament_id=tournament.id, team1_id=m['team1'], team2_id=m['team2'],
                date=m['date'], round_number=m['round_number'],
                phase='group', group_id=grp.id, group_letter=letter,
            ))

    total_group_rounds = max(len(generate_round_robin(ids)) * legs for ids in groups_dict.values())
    ko_start = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=7 * total_group_rounds + 7)).strftime('%Y-%m-%d')
    total_qualifiers = num_groups * qualify_per_group
    phases = auto_knockout_structure(total_qualifiers)
    _create_knockout_placeholders(tournament, phases, total_qualifiers, ko_start)


def _setup_pure_knockout(tournament, team_ids, start_date):
    for tid in team_ids:
        if not TournamentTeam.query.filter_by(tournament_id=tournament.id, team_id=tid).first():
            db.session.add(TournamentTeam(tournament_id=tournament.id, team_id=tid))

    phases = auto_knockout_structure(len(team_ids))
    first_phase = phases[0][0] if phases else 'final'
    matches = generate_knockout_bracket(team_ids, first_phase, start_date)
    for m in matches:
        db.session.add(Match(
            tournament_id=tournament.id, team1_id=m['team1'], team2_id=m['team2'],
            date=m['date'], round_number=m['round_number'], phase=m['phase'],
        ))


def _create_knockout_placeholders(tournament, phases, total_qualifiers, start_date):
    current = datetime.strptime(start_date, '%Y-%m-%d')
    num_matches = total_qualifiers // 2
    for phase_key, _ in phases:
        for _ in range(num_matches):
            db.session.add(Match(
                tournament_id=tournament.id, team1_id=1, team2_id=1,
                date=current.strftime('%Y-%m-%d'), round_number=1,
                phase=phase_key, status='scheduled',
            ))
        current += timedelta(days=14)
        num_matches = num_matches // 2
        if num_matches < 1:
            break


# ─── Room ─────────────────────────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>')
@login_required
def tournament_room(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    all_matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.date, Match.round_number).all()

    group_matches = [m for m in all_matches if m.phase == 'group']
    knockout_matches = [m for m in all_matches if m.phase != 'group']

    standings = TournamentTeam.query.filter_by(tournament_id=tournament_id).order_by(
        TournamentTeam.points.desc(), TournamentTeam.goals_for.desc()
    ).all()

    groups = Group.query.filter_by(tournament_id=tournament_id).all()

    from models.team import Player
    top_scorers = Player.query.join(
        TournamentTeam, Player.team_id == TournamentTeam.team_id
    ).filter(TournamentTeam.tournament_id == tournament_id).order_by(Player.goals.desc()).limit(5).all()

    # Teams not yet registered (for open registration)
    registered_ids = [tt.team_id for tt in standings]
    available_teams = Team.query.filter(Team.id.notin_(registered_ids)).order_by(Team.name).all()

    # Next matches
    today = datetime.today().strftime('%Y-%m-%d')
    next_matches = [m for m in all_matches if m.status == 'scheduled' and (m.date or '') >= today][:5]

    # Feed do campeonato
    from utils.feed_helpers import get_tournament_feed
    tournament_feed = get_tournament_feed(tournament_id, limit=30)

    return render_template('tournament/room.html',
                           tournament=tournament,
                           group_matches=group_matches,
                           knockout_matches=knockout_matches,
                           standings=standings,
                           groups=groups,
                           top_scorers=top_scorers,
                           available_teams=available_teams,
                           next_matches=next_matches,
                           today=today,
                           tournament_feed=tournament_feed)


# ─── Draw (sorteio de grupos) ─────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/draw')
@login_required
def draw_groups(tournament_id):
    """Página de sorteio de grupos com drag & drop."""
    tournament = Tournament.query.get_or_404(tournament_id)

    if tournament.type not in ('grupos_eliminatoria',):
        flash('Este torneio não tem fase de grupos.', 'error')
        return redirect(url_for('tournament.tournament_room', tournament_id=tournament_id))

    # Ensure groups exist in DB
    existing_groups = Group.query.filter_by(tournament_id=tournament_id).all()
    if not existing_groups:
        import string as _string
        num_groups = tournament.groups_count or 2
        for letter in _string.ascii_uppercase[:num_groups]:
            db.session.add(Group(name=letter, tournament_id=tournament_id))
        db.session.commit()

    registered_teams = TournamentTeam.query.filter_by(
        tournament_id=tournament_id
    ).order_by(TournamentTeam.group_letter.asc().nullslast()).all()

    return render_template('tournament/draw.html',
                           tournament=tournament,
                           registered_teams=registered_teams)


@tournament_bp.route('/tournaments/<int:tournament_id>/draw/save', methods=['POST'])
@login_required
@require_tournament_owner
def save_draw(tournament_id):
    """AJAX — save group assignments from drag & drop."""
    tournament = Tournament.query.get_or_404(tournament_id)
    data = request.get_json()

    if not data or 'assignments' not in data:
        return jsonify({'ok': False, 'error': 'Dados inválidos'}), 400

    assignments = data['assignments']  # {team_id: letter | null}

    # Ensure group objects exist
    existing = {g.name: g for g in Group.query.filter_by(tournament_id=tournament_id).all()}
    import string as _string
    num_groups = tournament.groups_count or 2
    for letter in _string.ascii_uppercase[:num_groups]:
        if letter not in existing:
            grp = Group(name=letter, tournament_id=tournament_id)
            db.session.add(grp)
            db.session.flush()
            existing[letter] = grp

    # Apply assignments
    for team_id_str, letter in assignments.items():
        team_id = int(team_id_str)
        tt = TournamentTeam.query.filter_by(
            tournament_id=tournament_id, team_id=team_id
        ).first()
        if not tt:
            continue

        if letter and letter in existing:
            tt.group_id = existing[letter].id
            tt.group_letter = letter
        else:
            tt.group_id = None
            tt.group_letter = None

    db.session.commit()
    return jsonify({'ok': True, 'saved': len(assignments)})


# ─── Jornadas (public) ────────────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/jornadas')
@tournament_bp.route('/tournaments/<int:tournament_id>/jornadas/<int:round_number>')
def jornadas(tournament_id, round_number=1):
    tournament = Tournament.query.get_or_404(tournament_id)

    all_group_matches = Match.query.filter_by(
        tournament_id=tournament_id, phase='group'
    ).order_by(Match.round_number, Match.date).all()

    total_rounds = max((m.round_number for m in all_group_matches), default=1)
    round_number = max(1, min(round_number, total_rounds))

    matches = [m for m in all_group_matches if m.round_number == round_number]

    return render_template('tournament/jornadas.html',
                           tournament=tournament,
                           round_number=round_number,
                           matches=matches,
                           total_rounds=total_rounds,
                           prev_round=round_number - 1 if round_number > 1 else None,
                           next_round=round_number + 1 if round_number < total_rounds else None)


# ─── Bracket (public) ─────────────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/bracket')
def bracket(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)

    knockout_matches = Match.query.filter(
        Match.tournament_id == tournament_id,
        Match.phase != 'group'
    ).order_by(Match.phase, Match.date).all()

    bracket_data = {}
    phase_order = ['round_of_16', 'quarter', 'semi', 'final']
    phase_labels = {
        'round_of_16': 'Oitavos',
        'quarter': 'Quartos',
        'semi': 'Meias-Finais',
        'final': 'Final',
    }

    for phase in phase_order:
        phase_matches = [m for m in knockout_matches if m.phase == phase]
        if phase_matches:
            bracket_data[phase] = {
                'label': phase_labels[phase],
                'matches': phase_matches,
            }

    return render_template('tournament/bracket.html',
                           tournament=tournament,
                           bracket_data=bracket_data,
                           phase_order=[p for p in phase_order if p in bracket_data])


# ─── Edit tournament info ─────────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/edit', methods=['GET', 'POST'])
@login_required
@require_tournament_owner
def edit_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    all_matches = Match.query.filter_by(tournament_id=tournament_id)\
        .order_by(Match.phase, Match.round_number, Match.date).all()

    if request.method == 'POST':
        f = request.form
        tournament.name             = f.get('name', tournament.name).strip()
        tournament.sport            = f.get('sport', tournament.sport)
        tournament.status           = f.get('status', tournament.status)
        tournament.start_date       = f.get('start_date', tournament.start_date or '').strip()
        tournament.description      = f.get('description', '').strip()
        tournament.type             = f.get('type', tournament.type)
        tournament.format_type      = f.get('format_type', tournament.format_type)
        tournament.teams_count      = int(f.get('teams_count') or tournament.teams_count or 0)
        tournament.groups_count     = int(f.get('groups_count') or 0)
        tournament.teams_per_group  = int(f.get('teams_per_group') or 0)
        tournament.qualify_per_group = int(f.get('qualify_per_group') or 2)
        tournament.group_legs       = int(f.get('group_legs') or 1)
        tournament.knockout_legs    = int(f.get('knockout_legs') or 1)
        tournament.has_groups       = 'has_groups'      in f
        tournament.has_knockout     = 'has_knockout'    in f
        tournament.has_round_of_16  = 'has_round_of_16' in f
        tournament.has_quarter      = 'has_quarter'     in f
        tournament.has_semi         = 'has_semi'        in f
        tournament.has_final        = 'has_final'       in f
        tournament.currency         = f.get('currency', tournament.currency or 'KWZ').strip()
        tournament.registration_fee  = float(f.get('registration_fee') or 0)
        tournament.participation_fee = float(f.get('participation_fee') or 0)
        tournament.prize_pool_total  = float(f.get('prize_pool_total') or 0)

        # Logo upload
        if 'logo' in request.files:
            f_logo = request.files['logo']
            if f_logo and f_logo.filename:
                from austinapp import allowed_file
                import uuid
                if allowed_file(f_logo.filename):
                    ext = f_logo.filename.rsplit('.', 1)[1].lower()
                    fname = f'tournament_{tournament.id}_{uuid.uuid4().hex[:8]}.{ext}'
                    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'logos', fname)
                    f_logo.save(save_path)
                    tournament.logo_url = f'uploads/logos/{fname}'

        db.session.commit()
        flash('✅ Torneio atualizado com sucesso!', 'success')
        return redirect(url_for('tournament.edit_tournament', tournament_id=tournament_id))

    return render_template('tournament/edit.html',
                           tournament=tournament,
                           all_matches=all_matches)


# ─── Edit matches (bulk save) ─────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/edit-matches', methods=['POST'])
@login_required
@require_tournament_owner
def edit_matches(tournament_id):
    from models.tournament import TournamentTeam

    tournament = Tournament.query.get_or_404(tournament_id)
    all_matches = Match.query.filter_by(tournament_id=tournament_id).all()

    for match in all_matches:
        mid = match.id
        new_date   = request.form.get(f'date_{mid}', '').strip()
        new_status = request.form.get(f'status_{mid}', match.status)
        score1_raw = request.form.get(f'score1_{mid}', '')
        score2_raw = request.form.get(f'score2_{mid}', '')

        if new_date:
            match.date = new_date
        match.status = new_status

        new_score1 = int(score1_raw) if score1_raw.strip().isdigit() else None
        new_score2 = int(score2_raw) if score2_raw.strip().isdigit() else None

        # If result changed and match is finished, recalculate standings
        if (new_status == 'finished' and
                new_score1 is not None and new_score2 is not None and
                (match.score1 != new_score1 or match.score2 != new_score2)):

            # Reverse old standings if match was already finished
            if match.status == 'finished' and match.score1 is not None:
                _reverse_standings(match)

            match.score1 = new_score1
            match.score2 = new_score2
            _update_standings_direct(match)
        else:
            if new_score1 is not None:
                match.score1 = new_score1
            if new_score2 is not None:
                match.score2 = new_score2

    db.session.commit()
    flash(f'✅ {len(all_matches)} jogos atualizados!', 'success')
    return redirect(url_for('tournament.edit_tournament', tournament_id=tournament_id) + '#tab-matches')


# ─── Bulk reschedule ──────────────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/bulk-reschedule', methods=['POST'])
@login_required
@require_manager
def bulk_reschedule(tournament_id):
    days_shift    = int(request.form.get('days_shift', 0) or 0)
    status_filter = request.form.get('status_filter', '')

    if days_shift == 0:
        flash('Indica um número de dias diferente de 0.', 'error')
        return redirect(url_for('tournament.edit_tournament', tournament_id=tournament_id) + '#tab-matches')

    query = Match.query.filter_by(tournament_id=tournament_id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    matches = query.all()
    updated = 0
    for match in matches:
        if match.date:
            try:
                old = datetime.strptime(match.date, '%Y-%m-%d')
                match.date = (old + timedelta(days=days_shift)).strftime('%Y-%m-%d')
                updated += 1
            except ValueError:
                pass

    db.session.commit()
    direction = 'avançados' if days_shift > 0 else 'recuados'
    flash(f'✅ {updated} jogos {direction} em {abs(days_shift)} dias.', 'success')
    return redirect(url_for('tournament.edit_tournament', tournament_id=tournament_id) + '#tab-matches')


# ─── Standings helpers ────────────────────────────────────────

def _reverse_standings(match):
    """Undo the effect of a finished match on standings."""
    from models.tournament import TournamentTeam
    t1 = TournamentTeam.query.filter_by(tournament_id=match.tournament_id, team_id=match.team1_id).first()
    t2 = TournamentTeam.query.filter_by(tournament_id=match.tournament_id, team_id=match.team2_id).first()
    if not t1 or not t2:
        return
    t1.played = max(0, t1.played - 1)
    t2.played = max(0, t2.played - 1)
    t1.goals_for    = max(0, t1.goals_for    - match.score1)
    t1.goals_against = max(0, t1.goals_against - match.score2)
    t2.goals_for    = max(0, t2.goals_for    - match.score2)
    t2.goals_against = max(0, t2.goals_against - match.score1)
    if match.score1 > match.score2:
        t1.wins   = max(0, t1.wins   - 1); t1.points = max(0, t1.points - 3)
        t2.losses = max(0, t2.losses - 1)
    elif match.score2 > match.score1:
        t2.wins   = max(0, t2.wins   - 1); t2.points = max(0, t2.points - 3)
        t1.losses = max(0, t1.losses - 1)
    else:
        t1.draws = max(0, t1.draws - 1); t1.points = max(0, t1.points - 1)
        t2.draws = max(0, t2.draws - 1); t2.points = max(0, t2.points - 1)


def _update_standings_direct(match):
    """Apply a finished match result to standings."""
    from models.tournament import TournamentTeam
    t1 = TournamentTeam.query.filter_by(tournament_id=match.tournament_id, team_id=match.team1_id).first()
    t2 = TournamentTeam.query.filter_by(tournament_id=match.tournament_id, team_id=match.team2_id).first()
    if not t1 or not t2:
        return
    t1.played += 1; t2.played += 1
    t1.goals_for    += match.score1; t1.goals_against += match.score2
    t2.goals_for    += match.score2; t2.goals_against += match.score1
    if match.score1 > match.score2:
        t1.wins += 1; t1.points += 3; t2.losses += 1
    elif match.score2 > match.score1:
        t2.wins += 1; t2.points += 3; t1.losses += 1
    else:
        t1.draws += 1; t2.draws += 1; t1.points += 1; t2.points += 1


# ─── Delete ───────────────────────────────────────────────────

@tournament_bp.route('/tournaments/<int:tournament_id>/delete', methods=['POST'])
@login_required
@require_manager
def delete_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    db.session.delete(tournament)
    db.session.commit()
    flash('Torneio eliminado.', 'info')
    return redirect(url_for('tournament.list_tournaments'))
