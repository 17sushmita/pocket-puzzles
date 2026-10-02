# Pocket Puzzles

Flask + PostgreSQL puzzle app with four practice games, daily ranked challenges,
portable username/password accounts, and mobile sharing/install support.
Scores and puzzle moves are validated by Flask; database credentials never go to the browser.

## Local development

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/setup_local.py
docker compose up -d db
.venv/bin/python -m puzzle.migrate
.venv/bin/gunicorn 'app:create_app()' --bind 0.0.0.0:4173 --workers 2 --threads 4
```

If your machine has standalone Compose, use `docker-compose` instead of `docker compose`.
Open http://127.0.0.1:4173. Local PostgreSQL uses port 55432 and a persistent Docker volume.
The setup script creates random secrets in ignored `.env` and preserves existing configuration.
For a containerized app, run `docker compose up --build` instead of Gunicorn.

Run `.venv/bin/pytest -q` for integration tests against local PostgreSQL. Tests create and
drop only their own temporary schemas. Never point tests at a production database.

## Render + Supabase deployment

1. Create a dedicated Supabase project. Keep the database password private.
2. In its **Connect** panel select **Session pooler** (port **5432**). Substitute the
   URL-encoded database password and append `?sslmode=require` (or `&sslmode=require`
   if the URL already contains parameters). Use the PostgreSQL URL, not an API key.
3. Push the active app source to a Git repository accessible by Render. Exclude `.env`,
   `.local`, `.venv`, and `node_modules`; `.gitignore` already does so.
4. Create a Render Blueprint from `render.yaml`. Enter the connection URL privately as
   `DATABASE_URL`. Keep the compute plan set to Free. This Blueprint creates
   only the Flask web service; it does not create another PostgreSQL database.
   Free Render services sleep after 15 minutes idle and may take about a minute to wake.
   Usage limits apply; free Supabase projects may pause after a week of inactivity.
5. Render generates `SECRET_KEY`. Keep `COOKIE_SECURE=true` and `TRUST_PROXY=true`.
   The start script applies versioned migrations before starting Gunicorn.
6. Verify `/healthz`, register a player, complete a daily challenge, and check its leaderboard.
   Share the Render HTTPS URL to play on phones. The Share button includes game/difficulty.

Use the Supabase database-owner connection for this setup. Migration 002 enables row-level
security with no browser policies on all app tables, blocking Supabase anonymous/authenticated
Data API access. Flask connects directly to PostgreSQL with the privileged backend account.
Supabase Auth is not used: Flask manages the app's accounts and hashed passwords.
Do not place the database URL or service-role keys in client files.

Session pooling supports the app's persistent PostgreSQL connections. See
[Supabase connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Mobile behavior and limits

The responsive interface supports touch, native sharing where available, and installation
on supported browsers. After an initial online visit, practice assets can be used offline;
accounts and ranked play require a connection. A localhost URL is not a public mobile link.
Daily challenges reset at midnight India time. Each account gets one ranked attempt per
game/difficulty/day. Password reset and email verification are not implemented yet.

## Preservation and rollback

`legacy-sites/` preserves the previous Node/Cloudflare implementation as a historical reference.
Its scripts assume the original layout; restore Git commit
`6b31167a04891712dadd2361131cc33b0aabff59` in a separate checkout to run it.
The original `.local/leaderboard.sqlite` is preserved. Its old identities and scores have
not been imported into PostgreSQL; the new account system starts fresh. No old hosted
database has been modified.

Back up PostgreSQL before future schema changes. Migrations are versioned and transactional;
do not edit previously applied migrations. Roll back application deployments to a compatible
release without dropping tables. Restore backups into a separate database before switching
`DATABASE_URL` if a data rollback is necessary. Keep `SECRET_KEY` stable across deployments
to preserve login sessions.
