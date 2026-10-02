"""Create local-only credentials once. Never replaces an existing configuration."""
from pathlib import Path
import secrets

path = Path(__file__).resolve().parents[1] / '.env'
if path.exists():
    print('Existing .env preserved.')
else:
    password = secrets.token_urlsafe(32)
    content = (f'DATABASE_URL=postgresql://puzzles:{password}@127.0.0.1:55432/puzzles\n'
               f'POSTGRES_PASSWORD={password}\nSECRET_KEY={secrets.token_hex(32)}\n'
               'COOKIE_SECURE=false\nTRUST_PROXY=false\nPORT=4173\n')
    with path.open('x') as file:
        file.write(content)
    path.chmod(0o600)
    print('Local configuration created in .env (ignored by Git).')
