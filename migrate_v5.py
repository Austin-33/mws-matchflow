"""AUSTIN LEAGUE CORE — Migration v5: Feed system tables."""
import os, sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')

def run():
    conn = sqlite3.connect(DB)
    conn.execute('PRAGMA foreign_keys = OFF')
    cur = conn.cursor()

    print('\n── feed_posts ──')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS feed_posts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            post_type     VARCHAR(20) DEFAULT "news",
            scope         VARCHAR(20) DEFAULT "global",
            title         VARCHAR(200),
            content       TEXT NOT NULL,
            image_url     VARCHAR(300),
            tournament_id INTEGER REFERENCES tournaments(id),
            match_id      INTEGER REFERENCES matches(id),
            author_id     INTEGER REFERENCES users(id),
            is_pinned     BOOLEAN DEFAULT 0,
            created_at    DATETIME
        )
    ''')
    print('  ✅ feed_posts')

    print('\n── feed_post_teams ──')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS feed_post_teams (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL REFERENCES feed_posts(id),
            team_id INTEGER NOT NULL REFERENCES teams(id)
        )
    ''')
    print('  ✅ feed_post_teams')

    conn.commit()
    conn.execute('PRAGMA foreign_keys = ON')
    conn.close()
    print('\n✅ Migration v5 complete!')

if __name__ == '__main__':
    run()
