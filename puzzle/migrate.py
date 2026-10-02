"""Transactional, versioned PostgreSQL migrations. Safe to rerun."""
import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

def migrate(url=None):
    load_dotenv(ROOT / '.env')
    with psycopg.connect(url or os.environ['DATABASE_URL']) as connection:
        connection.execute('SELECT pg_advisory_xact_lock(74829103)')
        connection.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())')
        for path in sorted((ROOT / 'migrations').glob('*.sql')):
            if not connection.execute('SELECT name FROM schema_migrations WHERE name=%s', (path.name,)).fetchone():
                connection.execute(path.read_text())
                connection.execute('INSERT INTO schema_migrations(name) VALUES(%s)', (path.name,))
                print(f'Applied {path.name}')

if __name__ == '__main__':
    migrate()
