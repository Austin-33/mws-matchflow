"""
AUSTIN LEAGUE CORE — Database Migration
Adds new columns to existing tables without losing data.
Run: python migrate_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join('instance', 'database.db')


def column_exists(cursor, table, column):
    cursor.execute(f'PRAGMA table_info({table})')
    return any(row[1] == column for row in cursor.fetchall())


def add_column(cursor, table, column, col_type, default=None):
    if not column_exists(cursor, table, column):
        default_clause = f" DEFAULT '{default}'" if default is not None else ''
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}')
        print(f'  ✅ Added {table}.{column}')
    else:
        print(f'  ⏭  {table}.{column} already exists')


def run():
    if not os.path.exists(DB_PATH):
        print('❌ Database not found. Run init_db.py first.')
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print('\n📦 Migrating teams table...')
    team_columns = [
        ('short_name',       'VARCHAR(10)',  None),
        ('founded_date',     'VARCHAR(20)',  None),
        ('city',             'VARCHAR(100)', None),
        ('country',          'VARCHAR(100)', 'Portugal'),
        ('primary_color',    'VARCHAR(10)',  '#2563eb'),
        ('secondary_color',  'VARCHAR(10)',  '#ffffff'),
        ('stadium',          'VARCHAR(100)', None),
        ('ceo',              'VARCHAR(100)', None),
        ('manager',          'VARCHAR(100)', None),
        ('assistant_coach',  'VARCHAR(100)', None),
        ('sport',            'VARCHAR(30)',  'futsal'),
        ('email',            'VARCHAR(150)', None),
        ('phone',            'VARCHAR(30)',  None),
        ('website',          'VARCHAR(200)', None),
        ('instagram',        'VARCHAR(100)', None),
        ('notes',            'TEXT',         None),
    ]
    for col, col_type, default in team_columns:
        add_column(cur, 'teams', col, col_type, default)

    print('\n📦 Migrating players table...')
    player_columns = [
        ('nickname',           'VARCHAR(50)',  None),
        ('secondary_position', 'VARCHAR(50)',  None),
        ('birth_date',         'VARCHAR(20)',  None),
        ('id_number',          'VARCHAR(30)',  None),
        ('phone',              'VARCHAR(30)',  None),
        ('email',              'VARCHAR(150)', None),
        ('height_cm',          'INTEGER',      None),
        ('weight_kg',          'INTEGER',      None),
        ('dominant_foot',      'VARCHAR(10)',  'Direito'),
        ('status',             'VARCHAR(20)',  'ativo'),
        ('contract_start',     'VARCHAR(20)',  None),
        ('contract_end',       'VARCHAR(20)',  None),
        ('minutes_played',     'INTEGER',      0),
    ]
    for col, col_type, default in player_columns:
        add_column(cur, 'players', col, col_type, default)

    print('\n📦 Migrating tournaments table...')
    tournament_columns = [
        ('sport',            'VARCHAR(50)',  'futsal'),
        ('has_groups',       'BOOLEAN',      0),
        ('teams_per_group',  'INTEGER',      0),
        ('qualify_per_group','INTEGER',      2),
        ('has_knockout',     'BOOLEAN',      0),
        ('has_round_of_16',  'BOOLEAN',      0),
        ('has_quarter',      'BOOLEAN',      0),
        ('has_semi',         'BOOLEAN',      1),
        ('has_final',        'BOOLEAN',      1),
    ]
    for col, col_type, default in tournament_columns:
        add_column(cur, 'tournaments', col, col_type, default)

    print('\n📦 Migrating matches table...')
    match_columns = [
        ('group_letter', 'VARCHAR(5)', None),
    ]
    for col, col_type, default in match_columns:
        add_column(cur, 'matches', col, col_type, default)

    print('\n📦 Migrating tournament_teams table...')
    tt_columns = [
        ('group_letter', 'VARCHAR(5)', None),
    ]
    for col, col_type, default in tt_columns:
        add_column(cur, 'tournament_teams', col, col_type, default)

    conn.commit()
    conn.close()
    print('\n✅ Migration complete!')


if __name__ == '__main__':
    run()
