import io, os, uuid
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, send_file, current_app)
from flask_login import login_required, current_user

from extensions import db
from models.team import Team, Player, TeamPost

team_bp = Blueprint('team', __name__)

POSITIONS_FUTSAL = ['GR', 'FIX', 'ALA-D', 'ALA-E', 'PV']
POSITIONS_FOOTBALL = ['GR', 'DD', 'DC', 'DE', 'MDC', 'MC', 'MO', 'ED', 'EE', 'PL', 'CA']
ALL_POSITIONS = sorted(set(POSITIONS_FUTSAL + POSITIONS_FOOTBALL))
FORMATIONS_FUTSAL = ['1-2-1', '1-3', '2-2', '3-1', '4-0']
FORMATIONS_FOOTBALL = ['4-3-3', '4-4-2', '4-2-3-1', '3-5-2', '5-3-2', '3-4-3', '4-1-4-1']


def _save_upload(file, subfolder):
    """Save uploaded image, return relative URL or None."""
    from app import allowed_file
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    fname = f'{subfolder}_{uuid.uuid4().hex[:10]}.{ext}'
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder, fname)
    file.save(path)
    return f'uploads/{subfolder}/{fname}'


# ─── List ─────────────────────────────────────────────────────

@team_bp.route('/teams')
@login_required
def list_teams():
    search = request.args.get('q', '').strip()
    sport_filter = request.args.get('sport', '')
    query = Team.query
    if search:
        query = query.filter(Team.name.ilike(f'%{search}%'))
    if sport_filter:
        query = query.filter_by(sport=sport_filter)
    teams = query.order_by(Team.name).all()
    return render_template('team/list.html', teams=teams, search=search, sport_filter=sport_filter)


# ─── Create ───────────────────────────────────────────────────

@team_bp.route('/teams/create', methods=['GET', 'POST'])
@login_required
def create_team():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('O nome é obrigatório.', 'error')
            return render_template('team/create.html', formations_football=FORMATIONS_FOOTBALL, formations_futsal=FORMATIONS_FUTSAL)
        if Team.query.filter_by(name=name).first():
            flash('Já existe uma equipa com esse nome.', 'error')
            return render_template('team/create.html', formations_football=FORMATIONS_FOOTBALL, formations_futsal=FORMATIONS_FUTSAL)

        team = Team(
            name=name,
            short_name=request.form.get('short_name', '').strip().upper(),
            founded_date=request.form.get('founded_date', '').strip(),
            city=request.form.get('city', '').strip(),
            country=request.form.get('country', 'Portugal').strip(),
            primary_color=request.form.get('primary_color', '#2563eb'),
            secondary_color=request.form.get('secondary_color', '#ffffff'),
            stadium=request.form.get('stadium', '').strip(),
            ceo=request.form.get('ceo', '').strip(),
            manager=request.form.get('manager', '').strip(),
            coach=request.form.get('coach', '').strip(),
            assistant_coach=request.form.get('assistant_coach', '').strip(),
            captain=request.form.get('captain', '').strip(),
            formation=request.form.get('formation', '4-3-3'),
            tactic=request.form.get('tactic', '').strip(),
            sport=request.form.get('sport', 'futsal'),
            email=request.form.get('email', '').strip(),
            phone=request.form.get('phone', '').strip(),
            website=request.form.get('website', '').strip(),
            instagram=request.form.get('instagram', '').strip(),
            notes=request.form.get('notes', '').strip(),
        )
        db.session.add(team)
        db.session.commit()

        # Logo upload
        logo_url = _save_upload(request.files.get('logo'), 'logos')
        if logo_url:
            team.logo_url = logo_url
            db.session.commit()

        flash(f'Equipa "{name}" criada! ⚽', 'success')
        return redirect(url_for('team.team_room', team_id=team.id))

    return render_template('team/create.html', formations_football=FORMATIONS_FOOTBALL, formations_futsal=FORMATIONS_FUTSAL)


# ─── Room ─────────────────────────────────────────────────────

@team_bp.route('/teams/<int:team_id>')
@login_required
def team_room(team_id):
    team = Team.query.get_or_404(team_id)
    players = Player.query.filter_by(team_id=team_id).order_by(Player.number).all()
    posts = TeamPost.query.filter_by(team_id=team_id).order_by(TeamPost.created_at.desc()).limit(20).all()

    active = [p for p in players if p.status == 'ativo']
    injured = [p for p in players if p.status == 'lesionado']
    suspended = [p for p in players if p.status == 'suspenso']
    inactive = [p for p in players if p.status == 'inativo']

    # Next matches for this team
    from models.match import Match
    from datetime import datetime
    today = datetime.today().strftime('%Y-%m-%d')
    next_matches = Match.query.filter(
        db.or_(Match.team1_id == team_id, Match.team2_id == team_id),
        Match.status == 'scheduled',
        Match.date >= today
    ).order_by(Match.date).limit(5).all()

    # Feed da equipa
    from utils.feed_helpers import get_team_feed
    team_feed_posts = get_team_feed(team_id, limit=20)

    return render_template('team/room.html', team=team, players=players, posts=posts,
                           active=active, injured=injured, suspended=suspended, inactive=inactive,
                           positions=ALL_POSITIONS, next_matches=next_matches,
                           team_feed_posts=team_feed_posts)


# ─── Edit ─────────────────────────────────────────────────────

@team_bp.route('/teams/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    if request.method == 'POST':
        team.name = request.form.get('name', team.name).strip()
        team.short_name = request.form.get('short_name', team.short_name or '').strip().upper()
        team.founded_date = request.form.get('founded_date', team.founded_date or '').strip()
        team.city = request.form.get('city', team.city or '').strip()
        team.country = request.form.get('country', team.country or 'Portugal').strip()
        team.primary_color = request.form.get('primary_color', team.primary_color or '#2563eb')
        team.secondary_color = request.form.get('secondary_color', team.secondary_color or '#ffffff')
        team.stadium = request.form.get('stadium', team.stadium or '').strip()
        team.ceo = request.form.get('ceo', team.ceo or '').strip()
        team.manager = request.form.get('manager', team.manager or '').strip()
        team.coach = request.form.get('coach', team.coach or '').strip()
        team.assistant_coach = request.form.get('assistant_coach', team.assistant_coach or '').strip()
        team.captain = request.form.get('captain', team.captain or '').strip()
        team.formation = request.form.get('formation', team.formation)
        team.tactic = request.form.get('tactic', team.tactic or '').strip()
        team.sport = request.form.get('sport', team.sport or 'futsal')
        team.email = request.form.get('email', team.email or '').strip()
        team.phone = request.form.get('phone', team.phone or '').strip()
        team.website = request.form.get('website', team.website or '').strip()
        team.instagram = request.form.get('instagram', team.instagram or '').strip()
        team.notes = request.form.get('notes', team.notes or '').strip()

        logo_url = _save_upload(request.files.get('logo'), 'logos')
        if logo_url:
            team.logo_url = logo_url

        db.session.commit()
        flash('Equipa atualizada! ✅', 'success')
        return redirect(url_for('team.team_room', team_id=team.id))

    return render_template('team/edit.html', team=team,
                           formations_football=FORMATIONS_FOOTBALL, formations_futsal=FORMATIONS_FUTSAL)


# ─── Delete ───────────────────────────────────────────────────

@team_bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@login_required
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    flash('Equipa eliminada.', 'info')
    return redirect(url_for('team.list_teams'))


# ─── Add Player ───────────────────────────────────────────────

@team_bp.route('/teams/<int:team_id>/players/add', methods=['POST'])
@login_required
def add_player(team_id):
    Team.query.get_or_404(team_id)
    player = Player(
        name=request.form.get('name', '').strip(),
        nickname=request.form.get('nickname', '').strip(),
        number=request.form.get('number', type=int),
        position=request.form.get('position', '').strip(),
        secondary_position=request.form.get('secondary_position', '').strip(),
        birth_date=request.form.get('birth_date', '').strip(),
        age=request.form.get('age', type=int),
        nationality=request.form.get('nationality', '').strip(),
        id_number=request.form.get('id_number', '').strip(),
        phone=request.form.get('phone', '').strip(),
        email=request.form.get('email', '').strip(),
        height_cm=request.form.get('height_cm', type=int),
        weight_kg=request.form.get('weight_kg', type=int),
        dominant_foot=request.form.get('dominant_foot', 'Direito'),
        status=request.form.get('status', 'ativo'),
        contract_start=request.form.get('contract_start', '').strip(),
        contract_end=request.form.get('contract_end', '').strip(),
        team_id=team_id,
    )
    db.session.add(player)
    db.session.commit()

    photo_url = _save_upload(request.files.get('photo'), 'players')
    if photo_url:
        player.photo_url = photo_url
        db.session.commit()

    flash(f'Jogador {player.name} adicionado! ✅', 'success')
    return redirect(url_for('team.team_room', team_id=team_id))


# ─── Edit Player ──────────────────────────────────────────────

@team_bp.route('/players/<int:player_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    if request.method == 'POST':
        player.name = request.form.get('name', player.name).strip()
        player.nickname = request.form.get('nickname', player.nickname or '').strip()
        player.number = request.form.get('number', type=int) or player.number
        player.position = request.form.get('position', player.position or '').strip()
        player.secondary_position = request.form.get('secondary_position', player.secondary_position or '').strip()
        player.birth_date = request.form.get('birth_date', player.birth_date or '').strip()
        player.age = request.form.get('age', type=int) or player.age
        player.nationality = request.form.get('nationality', player.nationality or '').strip()
        player.id_number = request.form.get('id_number', player.id_number or '').strip()
        player.phone = request.form.get('phone', player.phone or '').strip()
        player.email = request.form.get('email', player.email or '').strip()
        player.height_cm = request.form.get('height_cm', type=int) or player.height_cm
        player.weight_kg = request.form.get('weight_kg', type=int) or player.weight_kg
        player.dominant_foot = request.form.get('dominant_foot', player.dominant_foot or 'Direito')
        player.status = request.form.get('status', player.status or 'ativo')
        player.contract_start = request.form.get('contract_start', player.contract_start or '').strip()
        player.contract_end = request.form.get('contract_end', player.contract_end or '').strip()

        photo_url = _save_upload(request.files.get('photo'), 'players')
        if photo_url:
            player.photo_url = photo_url

        db.session.commit()
        flash('Jogador atualizado! ✅', 'success')
        return redirect(url_for('team.team_room', team_id=player.team_id))

    return render_template('team/edit_player.html', player=player, positions=ALL_POSITIONS)


# ─── Delete Player ────────────────────────────────────────────

@team_bp.route('/players/<int:player_id>/delete', methods=['POST'])
@login_required
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    team_id = player.team_id
    db.session.delete(player)
    db.session.commit()
    flash('Jogador removido.', 'info')
    return redirect(url_for('team.team_room', team_id=team_id))


# ─── Team Posts ───────────────────────────────────────────────

@team_bp.route('/teams/<int:team_id>/posts/add', methods=['POST'])
@login_required
def add_post(team_id):
    Team.query.get_or_404(team_id)
    content = request.form.get('content', '').strip()
    post_type = request.form.get('post_type', 'update')

    if not content:
        flash('Escreve algo antes de publicar.', 'error')
        return redirect(url_for('team.team_room', team_id=team_id))

    post = TeamPost(
        team_id=team_id,
        author_id=current_user.id,
        content=content,
        post_type=post_type,
    )
    db.session.add(post)
    db.session.commit()

    image_url = _save_upload(request.files.get('image'), 'posts')
    if image_url:
        post.image_url = image_url
        db.session.commit()

    flash('Publicação adicionada! 📢', 'success')
    return redirect(url_for('team.team_room', team_id=team_id))


@team_bp.route('/teams/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = TeamPost.query.get_or_404(post_id)
    team_id = post.team_id
    db.session.delete(post)
    db.session.commit()
    flash('Publicação removida.', 'info')
    return redirect(url_for('team.team_room', team_id=team_id))


# ─── Excel Import / Export ────────────────────────────────────

@team_bp.route('/teams/<int:team_id>/players/import', methods=['POST'])
@login_required
def import_players_excel(team_id):
    Team.query.get_or_404(team_id)
    if 'excel_file' not in request.files:
        flash('Nenhum ficheiro selecionado.', 'error')
        return redirect(url_for('team.team_room', team_id=team_id))

    file = request.files['excel_file']
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Formato inválido. Usa .xlsx ou .xls', 'error')
        return redirect(url_for('team.team_room', team_id=team_id))

    try:
        wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        ws = wb.active
        headers = [str(c.value or '').strip().lower() for c in ws[1]]
        col = {h: i for i, h in enumerate(headers)}

        def get(row, *keys):
            for k in keys:
                idx = col.get(k)
                if idx is not None and row[idx].value is not None:
                    return str(row[idx].value).strip()
            return ''

        def get_int(row, *keys):
            for k in keys:
                idx = col.get(k)
                if idx is not None:
                    try:
                        return int(row[idx].value)
                    except (TypeError, ValueError):
                        pass
            return None

        imported = skipped = 0
        for row in ws.iter_rows(min_row=2):
            if all(c.value is None for c in row):
                continue
            name = get(row, 'nome', 'name')
            if not name:
                skipped += 1
                continue
            if Player.query.filter_by(name=name, team_id=team_id).first():
                skipped += 1
                continue
            db.session.add(Player(
                name=name, nickname=get(row, 'alcunha', 'nickname'),
                number=get_int(row, 'nº', 'numero', 'number'),
                position=get(row, 'posição', 'posicao', 'position'),
                birth_date=get(row, 'data nascimento', 'nascimento', 'birth_date'),
                age=get_int(row, 'idade', 'age'),
                nationality=get(row, 'nacionalidade', 'nationality'),
                id_number=get(row, 'cc', 'id', 'passaporte'),
                phone=get(row, 'telefone', 'phone'),
                email=get(row, 'email'),
                height_cm=get_int(row, 'altura', 'height'),
                weight_kg=get_int(row, 'peso', 'weight'),
                dominant_foot=get(row, 'pé', 'pe', 'foot') or 'Direito',
                status=get(row, 'estado', 'status') or 'ativo',
                contract_start=get(row, 'contrato inicio', 'contract_start'),
                contract_end=get(row, 'contrato fim', 'contract_end'),
                team_id=team_id,
            ))
            imported += 1

        db.session.commit()
        wb.close()
        flash(f'✅ {imported} jogadores importados! ({skipped} ignorados)', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro: {e}', 'error')

    return redirect(url_for('team.team_room', team_id=team_id))


@team_bp.route('/teams/excel-template')
@login_required
def download_excel_template():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Jogadores'
    hf = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
    hfont = Font(bold=True, color='FFFFFF', size=11)
    headers = [('Nome *',25),('Alcunha',18),('Nº',6),('Posição',12),('Data Nascimento',18),
               ('Idade',8),('Nacionalidade',18),('CC',16),('Telefone',16),('Email',25),
               ('Altura',10),('Peso',8),('Pé',10),('Estado',12),('Contrato Inicio',16),('Contrato Fim',16)]
    for i,(h,w) in enumerate(headers,1):
        c = ws.cell(row=1,column=i,value=h)
        c.font=hfont; c.fill=hf; c.alignment=Alignment(horizontal='center')
        ws.column_dimensions[get_column_letter(i)].width=w
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='ALC_template_jogadores.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@team_bp.route('/teams/<int:team_id>/lineup/save', methods=['POST'])
@login_required
def save_team_lineup(team_id):
    """Save the tactical lineup for a team (not match-specific)."""
    from flask import jsonify
    team = Team.query.get_or_404(team_id)
    data = request.get_json()

    if not data:
        return jsonify({'ok': False, 'error': 'No data'}), 400

    formation = data.get('formation', team.formation)
    starters = data.get('starters', [])  # [{slot, player_id}]

    # Update team formation
    team.formation = formation

    # Store lineup as captain field hack — actually store in notes as JSON
    # In a real system you'd have a TeamLineup model; here we use a simple approach
    import json
    lineup_json = json.dumps({
        'formation': formation,
        'starters': starters
    })
    team.notes = (team.notes or '').split('__LINEUP__')[0] + f'__LINEUP__{lineup_json}'
    db.session.commit()

    return jsonify({'ok': True, 'formation': formation, 'count': len(starters)})


@team_bp.route('/teams/<int:team_id>/export')
@login_required
def export_team_excel(team_id):
    team = Team.query.get_or_404(team_id)
    players = Player.query.filter_by(team_id=team_id).order_by(Player.number).all()
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = team.name[:30]
    ws['A1'] = f'AUSTIN LEAGUE CORE — {team.name}'
    ws['A1'].font = Font(bold=True, size=14, color='2563EB')
    hf = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
    headers = ['Nº','Nome','Alcunha','Posição','Idade','Nac.','Alt.','Peso','Pé','Estado','⚽','🎯','🟨','🟥','Jogos']
    for i,h in enumerate(headers,1):
        c = ws.cell(row=3,column=i,value=h)
        c.font=Font(bold=True,color='FFFFFF'); c.fill=hf
    for ri,p in enumerate(players,4):
        row=[p.number,p.name,p.nickname,p.position,p.age,p.nationality,
             p.height_cm,p.weight_kg,p.dominant_foot,p.status,
             p.goals,p.assists,p.yellow_cards,p.red_cards,p.matches_played]
        for ci,v in enumerate(row,1):
            ws.cell(row=ri,column=ci,value=v)
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f'ALC_{team.name.replace(" ","_")}_plantel.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
