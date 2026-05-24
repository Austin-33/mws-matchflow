"""Migration v7: add format_type to tournaments."""
import os, sqlite3
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('PRAGMA table_info(tournaments)')
cols = [r[1] for r in cur.fetchall()]
if 'format_type' not in cols:
    cur.execute("ALTER TABLE tournaments ADD COLUMN format_type VARCHAR(20) DEFAULT 'liga'")
    conn.commit()
    print('Added format_type')
else:
    print('Already exists')
conn.close()
print('Done')
