"""Migration v8: tournament finance + awards tables."""
import os, sqlite3
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')

conn = sqlite3.connect(DB)
conn.execute('PRAGMA foreign_keys = OFF')
cur = conn.cursor()

# ── Add finance fields to tournaments ──────────────────────────
cur.execute('PRAGMA table_info(tournaments)')
cols = [r[1] for r in cur.fetchall()]

def add_col(table, col, typ, default=None):
    if col in cols:
        print(f'  skip {col}')
        return
    d = f" DEFAULT '{default}'" if default is not None else ''
    cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {typ}{d}')
    print(f'  + {col}')

add_col('tournaments', 'currency',           'VARCHAR(10)',  'KWZ')
add_col('tournaments', 'registration_fee',   'REAL',         0)
add_col('tournaments', 'participation_fee',  'REAL',         0)
add_col('tournaments', 'prize_pool_total',   'REAL',         0)

# ── tournament_awards table ────────────────────────────────────
cur.execute('''
    CREATE TABLE IF NOT EXISTS tournament_awards (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id   INTEGER NOT NULL REFERENCES tournaments(id),
        award_type      VARCHAR(30) NOT NULL,
        -- award_type: 1st | 2nd | 3rd | top_scorer | top_assist | mvp | best_gk | fair_play | custom
        label           VARCHAR(100),
        prize_value     REAL DEFAULT 0,
        prize_desc      VARCHAR(200),
        is_active       BOOLEAN DEFAULT 1,
        -- auto-filled after tournament ends
        winner_team_id  INTEGER REFERENCES teams(id),
        winner_player_id INTEGER REFERENCES players(id),
        created_at      DATETIME
    )
''')
print('  ✅ tournament_awards')

# ── team_payments table ────────────────────────────────────────
cur.execute('''
    CREATE TABLE IF NOT EXISTS team_payments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id   INTEGER NOT NULL REFERENCES tournaments(id),
        team_id         INTEGER NOT NULL REFERENCES teams(id),
        payment_type    VARCHAR(20) DEFAULT "registration",
        -- payment_type: registration | participation | penalty | other
        amount          REAL DEFAULT 0,
        currency        VARCHAR(10) DEFAULT "KWZ",
        status          VARCHAR(20) DEFAULT "pending",
        -- status: pending | paid | partial | waived
        paid_at         DATETIME,
        notes           VARCHAR(200),
        created_at      DATETIME
    )
''')
print('  ✅ team_payments')

conn.commit()
conn.execute('PRAGMA foreign_keys = ON')
conn.close()
print('\n✅ Migration v8 complete!')
