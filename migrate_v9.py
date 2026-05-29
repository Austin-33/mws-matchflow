"""
migrate_v9.py — Adiciona avatar_url à tabela users
Corre uma vez: python migrate_v9.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Verificar se a coluna já existe
    cur.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cur.fetchall()]

    if 'avatar_url' not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(300) DEFAULT ''")
        print("✅ Coluna avatar_url adicionada à tabela users.")
    else:
        print("ℹ️  Coluna avatar_url já existe — nada a fazer.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    run()
