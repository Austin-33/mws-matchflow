from flask import Blueprint, render_template, request
from flask_login import login_required

from extensions import db
from models.team import Player
from models.tournament import TournamentTeam

player_bp = Blueprint('player', __name__)


@player_bp.route('/ranking')
@login_required
def ranking():
    tournament_id = request.args.get('tournament_id', type=int)
    category = request.args.get('category', 'goals')

    from models.tournament import Tournament
    tournaments = Tournament.query.all()

    # Build ranking query
    query = Player.query

    if tournament_id:
        # Filter players that belong to teams in this tournament
        team_ids = [tt.team_id for tt in TournamentTeam.query.filter_by(tournament_id=tournament_id).all()]
        query = query.filter(Player.team_id.in_(team_ids))

    order_col = {
        'goals': Player.goals,
        'assists': Player.assists,
        'yellow_cards': Player.yellow_cards,
        'red_cards': Player.red_cards,
        'matches_played': Player.matches_played,
    }.get(category, Player.goals)

    players = query.order_by(order_col.desc()).limit(50).all()

    return render_template('player/ranking.html',
                           players=players,
                           tournaments=tournaments,
                           selected_tournament=tournament_id,
                           category=category)
