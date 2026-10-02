"""Flask entry point. Run with gunicorn 'app:create_app()'."""
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import time
import unicodedata
from datetime import timedelta
from functools import wraps
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, send_from_directory
from psycopg import Error as DatabaseError
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

from puzzle.games import GAMES, DIFFICULTIES, generate, advance, visible, day_key, reset_at

ROOT = Path(__file__).resolve().parent

class APIError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status

def require(condition, message, status=400):
    if not condition:
        raise APIError(message, status)

def create_app(config=None):
    load_dotenv(ROOT / '.env')
    app = Flask(__name__, static_folder=None)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY'), DATABASE_URL=os.environ.get('DATABASE_URL'),
        MAX_CONTENT_LENGTH=8192, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE','true').lower()=='true',
        SESSION_COOKIE_NAME='pocket_session', PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        NOW=lambda: int(time.time()*1000),
    )
    if config:
        app.config.update(config)
    if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('Set SECRET_KEY to a random value of at least 32 characters.')
    if not (app.config['DATABASE_URL'] or '').startswith(('postgresql://','postgres://')):
        raise RuntimeError('DATABASE_URL must point to PostgreSQL.')
    if os.environ.get('TRUST_PROXY','false').lower()=='true':
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    pool = ConnectionPool(app.config['DATABASE_URL'], min_size=0, max_size=5,
                          timeout=5, kwargs={'row_factory':dict_row,'connect_timeout':5}, open=True)
    app.extensions['db_pool'] = pool
    now = app.config['NOW']
    # Used when the username does not exist, so login still runs a password check.
    dummy_hash = generate_password_hash(secrets.token_hex(32))

    def body():
        require(request.is_json, 'Send JSON.')
        data = request.get_json(silent=True)
        require(isinstance(data,dict), 'Send a JSON object.')
        return data

    def options(data):
        game, difficulty = data.get('game'), data.get('difficulty')
        require(isinstance(game,str) and game in GAMES and isinstance(difficulty,str) and difficulty in DIFFICULTIES,
                'Choose a valid game and difficulty.')
        return game, difficulty

    def player_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            require(session.get('player_id'), 'Sign in to play ranked challenges.', 401)
            return fn(*args, **kwargs)
        return wrapped

    def display_name(value):
        name = ' '.join(value.split()) if isinstance(value,str) else ''
        require(2 <= len(name) <= 24 and not any(unicodedata.category(c).startswith('C') or c in '<>' for c in name),
                'Use 2–24 characters for your display name.')
        return name

    def auth_limit(username):
        # Persistent buckets shared by all workers. Do not store raw IP addresses.
        stamp=now()
        buckets=[('ip',request.remote_addr or 'unknown',60),('user',username,15)]
        with pool.connection() as db:
            db.execute('DELETE FROM auth_limits WHERE window_start < %s',(stamp-86400000,))
            for kind,value,limit in buckets:
                key=hmac.new(app.secret_key.encode(),f'{kind}:{value}'.encode(),hashlib.sha256).hexdigest()
                row=db.execute('''INSERT INTO auth_limits(key,window_start,count) VALUES(%s,%s,1)
                    ON CONFLICT(key) DO UPDATE SET
                    count=CASE WHEN auth_limits.window_start < %s THEN 1 ELSE auth_limits.count+1 END,
                    window_start=CASE WHEN auth_limits.window_start < %s THEN EXCLUDED.window_start ELSE auth_limits.window_start END
                    RETURNING count''',(key,stamp,stamp-900000,stamp-900000)).fetchone()
                if row['count'] > limit:
                    # Commit this bucket so a rejected request still consumes a try.
                    db.commit()
                    raise APIError('Too many sign-in attempts. Please try again in 15 minutes.',429)

    @app.before_request
    def csrf_protection():
        if request.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
            expected=session.get('csrf')
            require(expected and hmac.compare_digest(expected,request.headers.get('X-CSRF-Token','')),
                    'Your session changed. Refresh the page and try again.',403)
            origin=request.headers.get('Origin')
            require(not origin or origin.rstrip('/')==request.host_url.rstrip('/'),'Request origin is not allowed.',403)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['X-Frame-Options']='SAMEORIGIN'
        if request.path.startswith('/api/') or request.path=='/healthz':
            response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(APIError)
    def api_error(error):
        return jsonify(error=error.message), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(DatabaseError)
    @app.errorhandler(PoolTimeout)
    def db_error(error):
        app.logger.error('Database operation failed: %s',type(error).__name__)
        return jsonify(error='The leaderboard is temporarily unavailable. Please try again.'),503

    @app.get('/healthz')
    def health():
        with pool.connection() as db:
            db.execute('SELECT 1 FROM schema_migrations LIMIT 1').fetchone()
        return jsonify(status='ok',database='postgresql')

    @app.get('/api/session')
    def get_session():
        if 'csrf' not in session:
            session['csrf']=secrets.token_urlsafe(32)
        user=None
        if session.get('player_id'):
            with pool.connection() as db:
                row=db.execute('SELECT username,display_name FROM players WHERE id=%s',(session['player_id'],)).fetchone()
            if row:
                user={'username':row['username'],'profile':{'display_name':row['display_name']}}
            else:
                session.pop('player_id',None)
        return jsonify(user=user,csrfToken=session['csrf'],local=False)

    @app.post('/api/auth/<action>')
    def auth(action):
        require(action in ('register','login','logout'),'Not found.',404)
        if action=='logout':
            session.clear()
            session['csrf']=secrets.token_urlsafe(32)
            return jsonify(ok=True,csrfToken=session['csrf'])
        data=body()
        username=data.get('username','')
        require(isinstance(username,str),'Enter your username.')
        username=username.strip().lower()
        password=data.get('password','')
        require(re.fullmatch(r'[a-z0-9_]{3,24}',username),'Use 3–24 letters, numbers, or underscores for your username.')
        require(isinstance(password,str) and 1 <= len(password) <= 128,'Enter a password of at most 128 characters.')
        auth_limit(username)
        if action=='register':
            require(len(password)>=12,'Use a password of at least 12 characters.')
            name=display_name(data.get('name',username))
            player_id=str(uuid4())
            password_hash=generate_password_hash(password)
            try:
                with pool.connection() as db:
                    db.execute('INSERT INTO players(id,username,display_name,password_hash,created_at) VALUES(%s,%s,%s,%s,%s)',
                               (player_id,username,name,password_hash,now()))
            except UniqueViolation:
                raise APIError('That username is already taken.',409)
        else:
            with pool.connection() as db:
                row=db.execute('SELECT id,password_hash FROM players WHERE username=%s',(username,)).fetchone()
            valid=check_password_hash(row['password_hash'] if row else dummy_hash,password)
            require(row and valid,'Incorrect username or password.',401)
            player_id=row['id']
        session.clear()
        session['player_id']=player_id
        session['csrf']=secrets.token_urlsafe(32)
        session.permanent=True
        return jsonify(ok=True,csrfToken=session['csrf'])

    @app.put('/api/profile')
    @player_required
    def profile():
        name=display_name(body().get('name'))
        with pool.connection() as db:
            db.execute('UPDATE players SET display_name=%s WHERE id=%s',(name,session['player_id']))
        return jsonify(name=name)

    def challenge(db,game,difficulty,stamp):
        day=day_key(stamp)
        key=f'{day}:{game}:{difficulty}'
        row=db.execute('SELECT * FROM challenges WHERE id=%s',(key,)).fetchone()
        if not row:
            db.execute('INSERT INTO challenges(id,day,game,difficulty,puzzle,created_at) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                       (key,day,game,difficulty,Jsonb(generate(game,difficulty)),stamp))
            row=db.execute('SELECT * FROM challenges WHERE id=%s',(key,)).fetchone()
        return row

    def public_attempt(row,stamp):
        if not row:
            return None
        return dict(id=row['id'],revision=row['revision'],startedAt=row['started_at'],finishedAt=row['finished_at'],
                    elapsedMs=row['elapsed_ms'],state=visible(row['state'],stamp))

    def rankings(db,c,player_id):
        ranked='''SELECT a.player_id,p.display_name,a.moves,a.elapsed_ms,a.finished_at,
            RANK() OVER(ORDER BY a.moves,a.elapsed_ms) AS rank
            FROM attempts a JOIN players p ON p.id=a.player_id
            WHERE a.challenge_id=%s AND a.finished_at IS NOT NULL'''
        rows=db.execute('SELECT * FROM ('+ranked+') ranked ORDER BY rank,finished_at,player_id LIMIT 50',(c['id'],)).fetchall()
        mine=db.execute('SELECT * FROM ('+ranked+') ranked WHERE player_id=%s',(c['id'],player_id)).fetchone()
        count=db.execute('SELECT COUNT(*) AS total FROM attempts WHERE challenge_id=%s AND finished_at IS NOT NULL',(c['id'],)).fetchone()['total']
        best=db.execute('''SELECT MIN(a.moves) AS moves FROM attempts a JOIN challenges c ON c.id=a.challenge_id
            WHERE a.player_id=%s AND c.game=%s AND c.difficulty=%s AND a.finished_at IS NOT NULL''',(player_id,c['game'],c['difficulty'])).fetchone()['moves']
        def clean(r):
            return dict(rank=r['rank'],name=r['display_name'],moves=r['moves'],elapsedMs=r['elapsed_ms'],isYou=r['player_id']==player_id) if r else None
        return dict(rows=[clean(r) for r in rows],mine=clean(mine),count=count,personalBest=best,
                    gap=mine['moves']-rows[0]['moves'] if mine and rows else None)

    @app.get('/api/daily')
    @player_required
    def daily():
        game,difficulty=options(request.args)
        stamp=now()
        with pool.connection() as db:
            c=challenge(db,game,difficulty,stamp)
            row=db.execute('SELECT * FROM attempts WHERE player_id=%s AND challenge_id=%s',(session['player_id'],c['id'])).fetchone()
            board=rankings(db,c,session['player_id'])
        day=c['day'].isoformat()
        return jsonify(day=day,resetAt=reset_at(day),serverNow=stamp,attempt=public_attempt(row,stamp),leaderboard=board)

    @app.post('/api/start')
    @player_required
    def start():
        game,difficulty=options(body())
        stamp=now()
        with pool.connection() as db:
            c=challenge(db,game,difficulty,stamp)
            db.execute('''INSERT INTO attempts(id,player_id,challenge_id,state,started_at) VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT(player_id,challenge_id) DO NOTHING''',(str(uuid4()),session['player_id'],c['id'],Jsonb(c['puzzle']),stamp))
            row=db.execute('SELECT * FROM attempts WHERE player_id=%s AND challenge_id=%s',(session['player_id'],c['id'])).fetchone()
        return jsonify(attempt=public_attempt(row,stamp),serverNow=stamp)

    @app.post('/api/move')
    @player_required
    def move():
        data=body()
        attempt_id,revision,index=data.get('attemptId'),data.get('revision'),data.get('index')
        require(isinstance(attempt_id,str) and type(revision) is int and revision>=0 and type(index) is int,'Invalid move request.')
        with pool.connection() as db:
            row=db.execute('''SELECT a.*,c.day FROM attempts a JOIN challenges c ON c.id=a.challenge_id
                WHERE a.id=%s AND a.player_id=%s FOR UPDATE OF a''',(attempt_id,session['player_id'])).fetchone()
            require(row,'Attempt not found.',404)
            stamp=now()
            if row['revision']==revision+1 and row['last_index']==index:
                return jsonify(attempt=public_attempt(row,stamp),serverNow=stamp)
            require(row['day'].isoformat()==day_key(stamp),'This challenge has ended. Start today’s challenge.',410)
            require(row['revision']==revision,'Your attempt changed in another tab. Refresh to continue.',409)
            require(revision<10000,'This attempt reached the move limit.',409)
            try:
                state=advance(row['state'],index,stamp)
            except ValueError as error:
                raise APIError(str(error))
            result=db.execute('''UPDATE attempts SET state=%s,revision=revision+1,last_index=%s,moves=%s,finished_at=%s,elapsed_ms=%s
                WHERE id=%s RETURNING *''',(Jsonb(state),index,state['moves'],stamp if state['won'] else None,
                    max(1,stamp-row['started_at']) if state['won'] else None,attempt_id)).fetchone()
        return jsonify(attempt=public_attempt(result,stamp),serverNow=stamp)

    @app.get('/')
    def home():
        return send_from_directory(ROOT/'client','index.html',max_age=0)

    @app.get('/<path:filename>')
    def assets(filename):
        allowed={'app.js','ranked.js','mobile.js','style.css','manifest.webmanifest','sw.js','icon.svg','icon-192.png','icon-512.png'}
        require(filename in allowed,'Not found.',404)
        return send_from_directory(ROOT/'client',filename,max_age=0)

    return app
