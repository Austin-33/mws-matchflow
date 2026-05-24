"""Migration v6: feed_comments table."""
import os, sqlite3
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS feed_comments (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id    INTEGER NOT NULL REFERENCES feed_posts(id),
        author_id  INTEGER NOT NULL REFERENCES users(id),
        content    TEXT NOT NULL,
        created_at DATETIME
    )
''')
conn.commit()
conn.close()
print('✅ feed_comments created')
