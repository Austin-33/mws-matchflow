"""
Fix users table: remove NOT NULL constraint from password_hash
and add DEFAULT '' so users can be inserted before the hash is set.
SQLite does not support ALTER COLUMN, so we recreate the table.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')


def fix():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.cursor()

    print("Backing up users data...")
    cur.execute("SELECT id, public_id, username, email, password_hash, "
                "full_name, role, is_active, created_at, last_login, "
                "last_password_change, reset_token, reset_token_expires "
                "FROM users")
    rows = cur.fetchall()
    print(f"  {len(rows)} users found")

    print("Dropping old users table...")
    cur.execute("DROP TABLE IF EXISTS users_old")
    cur.execute("ALTER TABLE users RENAME TO users_old")

    print("Creating new users table with correct schema...")
    cur.execute("""
        CREATE TABLE users (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id           VARCHAR(36)  UNIQUE NOT NULL DEFAULT '',
            username            VARCHAR(100) UNIQUE NOT NULL,
            email               VARCHAR(150) UNIQUE NOT NULL,
            password_hash       VARCHAR(256) NOT NULL DEFAULT '',
            full_name           VARCHAR(150),
            role                VARCHAR(20)  DEFAULT 'manager',
            is_active           BOOLEAN      NOT NULL DEFAULT 1,
            created_at          DATETIME,
            last_login          DATETIME,
            last_password_change DATETIME,
            reset_token         VARCHAR(100) UNIQUE,
            reset_token_expires DATETIME
        )
    """)

    print("Restoring data...")
    for row in rows:
        (rid, public_id, username, email, pw_hash,
         full_name, role, is_active, created_at, last_login,
         last_pw_change, reset_token, reset_token_exp) = row

        # Fix NULLs
        pw_hash = pw_hash or ''
        public_id = public_id or ''
        is_active = 1 if is_active is None else int(bool(is_active))

        cur.execute("""
            INSERT INTO users
                (id, public_id, username, email, password_hash,
                 full_name, role, is_active, created_at, last_login,
                 last_password_change, reset_token, reset_token_expires)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (rid, public_id, username, email, pw_hash,
              full_name, role, is_active, created_at, last_login,
              last_pw_change, reset_token, reset_token_exp))

    cur.execute("DROP TABLE users_old")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # Verify
    cur.execute("PRAGMA table_info(users)")
    print("\nNew schema:")
    for col in cur.fetchall():
        notnull = "NOT NULL" if col[3] else "nullable"
        default = f"DEFAULT {col[4]}" if col[4] is not None else ""
        print(f"  {col[1]:25s} {col[2]:15s} {notnull:10s} {default}")

    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    print(f"\n✅ {count} users restored successfully!")
    conn.close()


if __name__ == '__main__':
    fix()
