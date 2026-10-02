#!/bin/sh
set -eu
python -m puzzle.migrate
exec gunicorn 'app:create_app()' --bind "0.0.0.0:${PORT:-8000}" --workers 2 --threads 4 --timeout 30 --access-logfile -
