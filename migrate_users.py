"""
AUSTIN LEAGUE CORE — User table migration
Adds new auth columns and creates password_history table.
Run: python migrate_users.py
"""
import uuid
import sqlite3
import os

DB_PATH = os.path.join('instance', 'database.db')


def column_exists(cursor, table, column):
    cursor.execute(f'PRAGMA table_info({table})')
    return any(row[1] == column for row in cursor.fetchall())


def add_column(cursor, table, column, col_type, default=None):
    if column_exists(cursor, table, column):
        print(f'  ⏭  {table}.{column} already exists')
        return
    if default is not None:
        cursor.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT '{default}'"
        )
    else:
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')
    print(f'  ✅ Added {table}.{column}')


def run():
    if not os.path.exists(DB_PATH):
        print('❌ Database not found. Run init_db.py first.')
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print('\n📦 Migrating users table...')
    add_column(cur, 'users', 'public_id',            'VARCHAR(36)',  None)
    add_column(cur, 'users', 'full_name',             'VARCHAR(150)', None)
    add_column(cur, 'users', 'is_active',             'BOOLEAN',      1)
    add_column(cur, 'users', 'last_login',            'DATETIME',     None)
    add_column(cur, 'users', 'last_password_change',  'DATETIME',     None)
    add_column(cur, 'users', 'reset_token',           'VARCHAR(100)', None)
    add_column(cur, 'users', 'reset_token_expires',   'DATETIME',     None)

    conn.commit()
    conn.close()

    # Create password_history table + assign public_ids via SQLAlchemy
    from app import app
    from extensions import db
    from models.user import User, PasswordHistory  # noqa: F401

    with app.app_context():
        db.create_all()  # creates password_history if not exists

        # Assign public_id to existing users that don't have one
        users_without_id = User.query.filter(User.public_id.is_(None)).all()
        for u in users_without_id:
            u.public_id = str(uuid.uuid4())
        db.session.commit()

        if users_without_id:
            print(f'\n✅ Assigned public_id to {len(users_without_id)} existing user(s)')

        # Verify
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f'\n📋 Tables: {tables}')

    print('\n✅ User migration complete!')


if __name__ == '__main__':
    run()
