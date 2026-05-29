"""
migrate_v10.py — Adiciona created_by_id a tournaments e matches
Corre uma vez: python migrate_v10.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for table, col in [
        ('tournaments', 'created_by_id'),
        ('matches',     'created_by_id'),
    ]:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cur.fetchall()]
        if col not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER REFERENCES users(id)")
            print(f"✅ {col} adicionado a {table}")
        else:
            print(f"ℹ️  {col} já existe em {table}")

    # Também adicionar status 'cancelled' ao match (já suportado pelo modelo)
    cur.execute("PRAGMA table_info(matches)")
    cols = [row[1] for row in cur.fetchall()]
    if 'cancelled_at' not in cols:
        cur.execute("ALTER TABLE matches ADD COLUMN cancelled_at DATETIME")
        print("✅ cancelled_at adicionado a matches")

    conn.commit()
    conn.close()
    print("Migração v10 concluída.")

if __name__ == '__main__':
    run()
