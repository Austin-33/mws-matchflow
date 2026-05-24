"""
AUSTIN LEAGUE CORE — Migration v3
Adds: MatchEvent, MatchLineup, TeamPost tables
Adds: new columns to matches, teams, players, tournaments
"""
import os, sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')

def col_exists(cur, table, col):
    cur.execute(f'PRAGMA table_info({table})')
    return any(r[1] == col for r in cur.fetchall())

def add_col(cur, table, col, typ, default=None):
    if col_exists(cur, table, col):
        print(f'  skip  {table}.{col}')
        return
    d = f" DEFAULT '{default}'" if default is not None else ''
    cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {typ}{d}')
    print(f'  +     {table}.{col}')

def run():
    conn = sqlite3.connect(DB)
    conn.execute('PRAGMA foreign_keys = OFF')
    cur = conn.cursor()

    print('\n── matches ──')
    add_col(cur, 'matches', 'minute_current', 'INTEGER', 0)

    print('\n── teams ──')
    add_col(cur, 'teams', 'logo_url', 'VARCHAR(300)', '')

    print('\n── players ──')
    add_col(cur, 'players', 'photo_url', 'VARCHAR(300)', '')

    print('\n── tournaments ──')
    add_col(cur, 'tournaments', 'description', 'TEXT', None)
    add_col(cur, 'tournaments', 'logo_url', 'VARCHAR(300)', '')
    add_col(cur, 'tournaments', 'group_legs', 'INTEGER', 1)
    add_col(cur, 'tournaments', 'knockout_legs', 'INTEGER', 1)

    print('\n── tournament_teams ──')
    add_col(cur, 'tournament_teams', 'seed', 'INTEGER', 0)

    # Create new tables
    print('\n── match_events ──')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS match_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id    INTEGER NOT NULL REFERENCES matches(id),
            minute      INTEGER DEFAULT 0,
            event_type  VARCHAR(30) NOT NULL,
            team_id     INTEGER REFERENCES teams(id),
            player_id   INTEGER REFERENCES players(id),
            player2_id  INTEGER REFERENCES players(id),
            description VARCHAR(200),
            created_at  DATETIME
        )
    ''')
    print('  ✅ match_events')

    print('\n── match_lineups ──')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS match_lineups (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id          INTEGER NOT NULL REFERENCES matches(id),
            team_id           INTEGER NOT NULL REFERENCES teams(id),
            player_id         INTEGER NOT NULL REFERENCES players(id),
            is_starter        BOOLEAN DEFAULT 1,
            position_override VARCHAR(20),
            shirt_number      INTEGER,
            formation         VARCHAR(20)
        )
    ''')
    print('  ✅ match_lineups')

    print('\n── team_posts ──')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS team_posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id    INTEGER NOT NULL REFERENCES teams(id),
            author_id  INTEGER REFERENCES users(id),
            content    TEXT NOT NULL,
            image_url  VARCHAR(300),
            post_type  VARCHAR(20) DEFAULT "update",
            created_at DATETIME
        )
    ''')
    print('  ✅ team_posts')

    conn.commit()
    conn.execute('PRAGMA foreign_keys = ON')
    conn.close()
    print('\n✅ Migration v3 complete!')

if __name__ == '__main__':
    run()
