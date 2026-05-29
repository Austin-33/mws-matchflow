"""AUSTIN LEAGUE CORE — Feed Routes."""
import os, uuid
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user

from extensions import db
from models.feed import FeedPost, FeedPostTeam, FeedComment
from models.team import Team
from utils.feed_helpers import get_global_feed, get_team_feed, get_tournament_feed

feed_bp = Blueprint('feed', __name__)


# ─── Feed Global ──────────────────────────────────────────────

@feed_bp.route('/feed')
@login_required
def global_feed():
    posts = get_global_feed(limit=60)
    teams = Team.query.filter(Team.name != '__FREE_AGENTS__').order_by(Team.name).all()
    from models.tournament import Tournament
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template('feed/global.html', posts=posts, teams=teams, tournaments=tournaments)


# ─── Criar post (organização) ─────────────────────────────────

@feed_bp.route('/feed/create', methods=['POST'])
@login_required
def create_post():
    if current_user.role not in ('admin', 'manager'):
        flash('Sem permissão para publicar.', 'error')
        return redirect(url_for('feed.global_feed'))

    post_type = request.form.get('post_type', 'news')
    scope = request.form.get('scope', 'global')
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    tournament_id = request.form.get('tournament_id', type=int)
    tagged_team_ids = request.form.getlist('tagged_teams')

    if not content:
        flash('O conteúdo não pode estar vazio.', 'error')
        return redirect(url_for('feed.global_feed'))

    post = FeedPost(
        post_type=post_type,
        scope=scope,
        title=title or None,
        content=content,
        tournament_id=tournament_id or None,
        author_id=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.session.add(post)
    db.session.flush()

    # Handle image upload
    if 'image' in request.files:
        img = request.files['image']
        if img and img.filename:
            from austinapp import allowed_file
            if allowed_file(img.filename):
                ext = img.filename.rsplit('.', 1)[1].lower()
                fname = f'feed_{uuid.uuid4().hex[:10]}.{ext}'
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'posts', fname)
                img.save(path)
                post.image_url = f'uploads/posts/{fname}'

    # Tag teams
    for tid in tagged_team_ids:
        if tid:
            db.session.add(FeedPostTeam(post_id=post.id, team_id=int(tid)))

    # If scope is team and teams tagged, also set scope
    if tagged_team_ids and scope == 'team':
        post.scope = 'team'

    db.session.commit()
    flash('✅ Publicação criada!', 'success')

    # Redirect back to origin
    next_url = request.form.get('next') or url_for('feed.global_feed')
    return redirect(next_url)


# ─── Apagar post ──────────────────────────────────────────────

@feed_bp.route('/feed/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = FeedPost.query.get_or_404(post_id)
    if current_user.role not in ('admin', 'manager') and post.author_id != current_user.id:
        flash('Sem permissão.', 'error')
        return redirect(url_for('feed.global_feed'))
    db.session.delete(post)
    db.session.commit()
    flash('Publicação removida.', 'info')
    next_url = request.form.get('next') or url_for('feed.global_feed')
    return redirect(next_url)


# ─── Pin/Unpin post ───────────────────────────────────────────

@feed_bp.route('/feed/<int:post_id>/pin', methods=['POST'])
@login_required
def toggle_pin(post_id):
    if current_user.role not in ('admin', 'manager'):
        return jsonify({'ok': False}), 403
    post = FeedPost.query.get_or_404(post_id)
    post.is_pinned = not post.is_pinned
    db.session.commit()
    return jsonify({'ok': True, 'pinned': post.is_pinned})


# ─── API: ticker (rodapé dinâmico) ────────────────────────────

@feed_bp.route('/feed/ticker')
def ticker():
    """JSON endpoint para o rodapé dinâmico de resultados."""
    from utils.feed_helpers import get_ticker_results
    results = get_ticker_results(limit=15)
    return jsonify([{
        'id': p.id,
        'title': p.title,
        'created_at': p.created_at.strftime('%d/%m %H:%M') if p.created_at else '',
    } for p in results])


# ─── Comentários ──────────────────────────────────────────────

@feed_bp.route('/feed/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = FeedPost.query.get_or_404(post_id)
    content = request.get_json().get('content', '').strip() if request.is_json else request.form.get('content', '').strip()

    if not content:
        return jsonify({'ok': False, 'error': 'Comentário vazio'}), 400

    comment = FeedComment(
        post_id=post_id,
        author_id=current_user.id,
        content=content,
        created_at=datetime.utcnow(),
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        'ok': True,
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'author': current_user.display_name,
            'author_initial': current_user.display_name[0].upper(),
            'created_at': comment.created_at.strftime('%d/%m %H:%M'),
        }
    })


@feed_bp.route('/feed/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = FeedComment.query.get_or_404(comment_id)
    if comment.author_id != current_user.id and current_user.role not in ('admin', 'manager'):
        return jsonify({'ok': False, 'error': 'Sem permissão'}), 403
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'ok': True})


# ─── Post de jornada completa ─────────────────────────────────

@feed_bp.route('/feed/post-round/<int:tournament_id>/<int:round_number>', methods=['POST'])
@login_required
def post_round_results(tournament_id, round_number):
    """Cria um post de feed com todos os resultados de uma jornada."""
    if current_user.role not in ('admin', 'manager'):
        return jsonify({'ok': False, 'error': 'Sem permissão'}), 403

    from models.match import Match
    from models.tournament import Tournament
    from models.feed import FeedPostTeam

    tournament = Tournament.query.get_or_404(tournament_id)
    matches = Match.query.filter_by(
        tournament_id=tournament_id,
        round_number=round_number,
        phase='group',
        status='finished'
    ).all()

    if not matches:
        return jsonify({'ok': False, 'error': 'Sem jogos terminados nesta jornada'}), 400

    # Check for existing round post
    existing = FeedPost.query.filter_by(
        tournament_id=tournament_id,
        post_type='result',
        title=f'Jornada {round_number} — {tournament.name}'
    ).first()
    if existing:
        return jsonify({'ok': False, 'error': 'Jornada já publicada no feed'}), 400

    lines = [f'📅 {tournament.start_date or ""}', '']
    team_ids = set()
    for m in matches:
        if m.score1 is not None and m.score2 is not None:
            if m.score1 > m.score2:
                line = f'🏆 {m.team1.name}  {m.score1} – {m.score2}  {m.team2.name}'
            elif m.score2 > m.score1:
                line = f'{m.team1.name}  {m.score1} – {m.score2}  {m.team2.name} 🏆'
            else:
                line = f'🤝 {m.team1.name}  {m.score1} – {m.score2}  {m.team2.name}'
            lines.append(line)
            team_ids.add(m.team1_id)
            team_ids.add(m.team2_id)

    post = FeedPost(
        post_type='result',
        scope='global',
        title=f'Jornada {round_number} — {tournament.name}',
        content='\n'.join(lines),
        tournament_id=tournament_id,
        author_id=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.session.add(post)
    db.session.flush()

    for tid in team_ids:
        db.session.add(FeedPostTeam(post_id=post.id, team_id=tid))

    db.session.commit()
    return jsonify({'ok': True, 'post_id': post.id})
