"""Fix NULL values in users table from migration."""
import sqlite3
import os

DB = os.path.join('instance', 'database.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
cur.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
conn.commit()

cur.execute("SELECT id, username, is_active, length(password_hash) as pw_len FROM users")
print("Users after fix:")
for row in cur.fetchall():
    print(f"  id={row[0]} username={row[1]} is_active={row[2]} pw_hash_len={row[3]}")

conn.close()
print("Done!")
