"""
AUSTIN LEAGUE CORE — Scheduler
Geração automática de calendários, grupos e fases eliminatórias.
"""
import random
import string
from datetime import datetime, timedelta


# ─── Round-Robin ──────────────────────────────────────────────

def generate_round_robin(teams):
    """
    Full round-robin for a list of team IDs.
    Returns list of rounds: each round = list of (team1_id, team2_id).
    """
    teams = list(teams)
    if len(teams) % 2 != 0:
        teams.append('BYE')

    n = len(teams)
    rounds = []

    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            t1 = teams[i]
            t2 = teams[n - 1 - i]
            if t1 != 'BYE' and t2 != 'BYE':
                pairs.append((t1, t2))
        # Rotate keeping first fixed
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        rounds.append(pairs)

    return rounds


def assign_dates(schedule, start_date_str, days_between=7):
    """
    Assigns dates to each round.
    Returns flat list of dicts: {team1, team2, date, round_number, phase}.
    """
    dated = []
    current = datetime.strptime(start_date_str, '%Y-%m-%d')

    for round_num, round_matches in enumerate(schedule, start=1):
        for t1, t2 in round_matches:
            dated.append({
                'team1': t1,
                'team2': t2,
                'date': current.strftime('%Y-%m-%d'),
                'round_number': round_num,
                'phase': 'group',
            })
        current += timedelta(days=days_between)

    return dated


# ─── Groups ───────────────────────────────────────────────────

def generate_groups(team_ids, num_groups):
    """
    Distributes team IDs into groups as evenly as possible.
    Returns dict: {'A': [id1, id2, ...], 'B': [...], ...}
    """
    teams = list(team_ids)
    random.shuffle(teams)

    letters = list(string.ascii_uppercase[:num_groups])
    groups = {letter: [] for letter in letters}

    for i, tid in enumerate(teams):
        groups[letters[i % num_groups]].append(tid)

    return groups


# ─── Knockout ─────────────────────────────────────────────────

def generate_knockout_bracket(team_ids, phase_name, start_date_str, days_between=7):
    """
    Single-elimination bracket from a list of team IDs.
    Returns list of match dicts.
    """
    teams = list(team_ids)
    matches = []
    current = datetime.strptime(start_date_str, '%Y-%m-%d')

    for i in range(0, len(teams) - 1, 2):
        matches.append({
            'team1': teams[i],
            'team2': teams[i + 1],
            'date': current.strftime('%Y-%m-%d'),
            'round_number': 1,
            'phase': phase_name,
        })
        current += timedelta(days=days_between)

    return matches


# ─── Auto-detection ───────────────────────────────────────────

def auto_knockout_structure(num_teams):
    """
    Returns ordered list of (phase_key, label) based on team count.
    """
    if num_teams >= 16:
        return [
            ('round_of_16', 'Oitavos de Final'),
            ('quarter', 'Quartos de Final'),
            ('semi', 'Meia-Final'),
            ('final', '🏆 Final'),
        ]
    elif num_teams >= 8:
        return [
            ('quarter', 'Quartos de Final'),
            ('semi', 'Meia-Final'),
            ('final', '🏆 Final'),
        ]
    elif num_teams >= 4:
        return [
            ('semi', 'Meia-Final'),
            ('final', '🏆 Final'),
        ]
    else:
        return [('final', '🏆 Final')]


def get_phase_name(num_teams):
    """Returns the first phase key for a given number of teams."""
    phases = auto_knockout_structure(num_teams)
    return phases[0][0] if phases else 'final'
