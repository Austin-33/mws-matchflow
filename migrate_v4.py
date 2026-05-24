"""
AUSTIN LEAGUE CORE — Migration v4
Adds: sport_role, player_id, preferred_position, current_team_id to users
Creates: transfer_requests table
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

    print('\n── users ──')
    add_col(cur, 'users', 'sport_role',          'VARCHAR(20)',  'player')
    add_col(cur, 'users', 'player_id',            'INTEGER',      None)
    add_col(cur, 'users', 'preferred_position',   'VARCHAR(50)',  None)
    add_col(cur, 'users', 'current_team_id',      'INTEGER',      None)

    print('\n── transfer_requests ──')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transfer_requests (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL REFERENCES users(id),
            team_id          INTEGER NOT NULL REFERENCES teams(id),
            request_type     VARCHAR(20) DEFAULT "contract",
            status           VARCHAR(20) DEFAULT "pending",
            message          TEXT,
            response_message TEXT,
            reviewed_by_id   INTEGER REFERENCES users(id),
            created_at       DATETIME,
            reviewed_at      DATETIME
        )
    ''')
    print('  ✅ transfer_requests')

    # Set sport_role for existing users based on their role
    cur.execute("UPDATE users SET sport_role = role WHERE sport_role IS NULL OR sport_role = ''")
    print('\n  ✅ Existing users sport_role synced with role')

    conn.commit()
    conn.execute('PRAGMA foreign_keys = ON')
    conn.close()
    print('\n✅ Migration v4 complete!')

if __name__ == '__main__':
    run()
