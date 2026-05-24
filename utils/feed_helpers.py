"""
AUSTIN LEAGUE CORE — Feed Helpers
Funções para criar posts automáticos no feed.
"""
from datetime import datetime
from extensions import db


def create_match_result_post(match):
    """
    Cria automaticamente um FeedPost de resultado quando um jogo termina.
    Marca as duas equipas e o campeonato.
    """
    from models.feed import FeedPost, FeedPostTeam

    # Evitar duplicados
    existing = FeedPost.query.filter_by(match_id=match.id, post_type='result').first()
    if existing:
        return existing

    # Determinar vencedor
    if match.score1 > match.score2:
        winner = match.team1.name
        result_emoji = '🏆'
    elif match.score2 > match.score1:
        winner = match.team2.name
        result_emoji = '🏆'
    else:
        winner = None
        result_emoji = '🤝'

    phase_label = match.phase_label
    round_label = f'Jornada {match.round_number}' if match.phase == 'group' else phase_label

    title = f'{result_emoji} {match.team1.name} {match.score1}–{match.score2} {match.team2.name}'

    # Build content with top scorers
    lines = [
        f'**{match.tournament.name}** · {round_label}',
        f'📅 {match.date}',
        '',
    ]

    if winner:
        lines.append(f'🏆 Vitória de **{winner}**!')
    else:
        lines.append('🤝 Empate!')

    # Add top scorers from events
    goals = [e for e in match.events if e.event_type in ('goal', 'penalty', 'own_goal')]
    if goals:
        lines.append('')
        lines.append('⚽ **Marcadores:**')
        for g in goals:
            scorer = g.player.display_name if g.player else '?'
            team_name = g.team.name if g.team else '?'
            own = ' (autogolo)' if g.event_type == 'own_goal' else ''
            lines.append(f"  {g.minute}' {scorer} ({team_name}){own}")

    content = '\n'.join(lines)

    post = FeedPost(
        post_type='result',
        scope='global',
        title=title,
        content=content,
        tournament_id=match.tournament_id,
        match_id=match.id,
        created_at=datetime.utcnow(),
    )
    db.session.add(post)
    db.session.flush()

    # Tag both teams
    for team_id in [match.team1_id, match.team2_id]:
        db.session.add(FeedPostTeam(post_id=post.id, team_id=team_id))

    db.session.commit()
    return post


def get_team_feed(team_id, limit=20):
    """Retorna posts do feed de uma equipa (marcados com essa equipa)."""
    from models.feed import FeedPost, FeedPostTeam
    return (
        FeedPost.query
        .join(FeedPostTeam, FeedPost.id == FeedPostTeam.post_id)
        .filter(FeedPostTeam.team_id == team_id)
        .order_by(FeedPost.is_pinned.desc(), FeedPost.created_at.desc())
        .limit(limit)
        .all()
    )


def get_tournament_feed(tournament_id, limit=30):
    """Retorna posts do feed de um campeonato."""
    from models.feed import FeedPost
    return (
        FeedPost.query
        .filter(
            db.or_(
                FeedPost.tournament_id == tournament_id,
                FeedPost.scope == 'global'
            )
        )
        .order_by(FeedPost.is_pinned.desc(), FeedPost.created_at.desc())
        .limit(limit)
        .all()
    )


def get_global_feed(limit=50):
    """Retorna o feed global (todos os posts públicos)."""
    from models.feed import FeedPost
    return (
        FeedPost.query
        .filter(FeedPost.scope.in_(['global', 'tournament']))
        .order_by(FeedPost.is_pinned.desc(), FeedPost.created_at.desc())
        .limit(limit)
        .all()
    )


def get_ticker_results(limit=10):
    """Últimos resultados para o rodapé dinâmico."""
    from models.feed import FeedPost
    return (
        FeedPost.query
        .filter_by(post_type='result')
        .order_by(FeedPost.created_at.desc())
        .limit(limit)
        .all()
    )
