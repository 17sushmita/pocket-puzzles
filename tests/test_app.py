from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from pathlib import Path
from app import create_app
from conftest import api,register,start
from puzzle.games import generate,advance,neighbors,visible,day_key,reset_at
from puzzle.migrate import migrate

def lights_solution(board,n):
    # Row-chasing solver independent from generator; enumerate the first row only.
    for mask in range(1<<n):
        b=board[:];moves=[]
        def press(i):
            moves.append(i)
            for j in [i]+neighbors(i,n): b[j]^=1
        for i in range(n):
            if mask&(1<<i):press(i)
        for row in range(1,n):
            for col in range(n):
                if b[(row-1)*n+col]:press(row*n+col)
        if not any(b):return moves
    raise AssertionError('Unsolvable board')

def test_puzzle_generators_and_rules():
    for difficulty in ('easy','tricky'):
        for _ in range(6):
            s=generate('lights',difficulty)
            for i in lights_solution(s['board'],s['n']):s=advance(s,i,1)
            assert s['won']
            s=generate('slide',difficulty);tiles=[v for v in s['board'] if v]
            inversions=sum(a>b for i,a in enumerate(tiles) for b in tiles[i+1:])
            row=s['n']-s['board'].index(0)//s['n']
            assert inversions%2==0 if s['n']%2 else (inversions+row)%2==1
        s=generate('memory',difficulty);deck=s['board'][:]
        for v in set(deck):
            for i,x in enumerate(deck):
                if x==v:s=advance(s,i,1)
        assert s['won'] and s['moves']==len(deck)//2
        assert visible(s,1)['board']==deck
        s=generate('flood',difficulty)
        for i in range(600):
            if s['won']:break
            if i%6!=s['board'][0]:s=advance(s,i%6,1)
        assert s['won']

def test_auth_csrf_and_password_hash(client,app):
    assert client.get('/api/daily?game=lights&difficulty=easy',headers={'oai-authenticated-user-id':'forged','oai-authenticated-user-email':'x@y.z'}).status_code==401
    assert client.post('/api/auth/register',json={}).status_code==403
    assert register(client).status_code==200
    with app.extensions['db_pool'].connection() as db:
        assert db.execute('SELECT password_hash FROM players').fetchone()['password_hash'].startswith('scrypt:')
    assert api(client,'/api/auth/logout').status_code==200
    assert api(client,'/api/auth/login',{'username':'alice','password':'wrong'}).status_code==401
    assert api(client,'/api/auth/login',{'username':'alice','password':'a-test-password-123'}).status_code==200
    assert client.get('/api/session').get_json()['user']['username']=='alice'

def test_csrf_origin_and_validation(client):
    register(client)
    csrf=client.get('/api/session').get_json()['csrfToken']
    assert client.put('/api/profile',json={'name':'New'},headers={'X-CSRF-Token':csrf,'Origin':'https://evil.test'}).status_code==403
    assert api(client,'/api/profile',{'name':'<script>'},'PUT').status_code==400
    assert api(client,'/api/start',{'game':['lights'],'difficulty':'easy'}).status_code==400
    assert api(client,'/api/auth/register',{'username':'bob','password':'short','name':'Bob'}).status_code==400

def test_shared_daily_board_first_attempt_and_server_scores(client,app):
    register(client);a=start(client)
    other=app.test_client();register(other,'bob');b=start(other)
    assert a['state']['board']==b['state']['board']
    assert start(client)['id']==a['id']
    assert api(other,'/api/move',{'attemptId':a['id'],'revision':0,'index':0}).status_code==404
    moves=lights_solution(a['state']['board'],4)
    for index in moves:
        app.clock[0]+=1000
        response=api(client,'/api/move',{'attemptId':a['id'],'revision':a['revision'],'index':index,'moves':0,'elapsedMs':0})
        assert response.status_code==200
        a=response.get_json()['attempt']
    assert a['state']['won'] and a['state']['moves']==len(moves)
    assert a['elapsedMs']==len(moves)*1000
    data=client.get('/api/daily?game=lights&difficulty=easy').get_json()
    assert data['leaderboard']['mine']['rank']==1 and data['leaderboard']['count']==1
    assert data['leaderboard']['personalBest']==len(moves)
    assert start(client)['state']['won']

def test_retries_and_stale_tabs(client,app):
    register(client);a=start(client);payload={'attemptId':a['id'],'revision':0,'index':0}
    one=api(client,'/api/move',payload).get_json()['attempt']
    assert api(client,'/api/move',payload).get_json()['attempt']['revision']==one['revision']
    assert api(client,'/api/move',{**payload,'index':1}).status_code==409
    assert api(client,'/api/move',{**payload,'revision':1,'index':True}).status_code==400

def test_concurrent_moves_serialized_by_postgres(client,app):
    register(client);a=start(client)
    csrf=client.get('/api/session').get_json()['csrfToken'];cookie=client.get_cookie('pocket_session').value
    def perform(index):
        other=app.test_client();other.set_cookie('pocket_session',cookie)
        return other.post('/api/move',json={'attemptId':a['id'],'revision':0,'index':index},headers={'X-CSRF-Token':csrf}).status_code
    with ThreadPoolExecutor(max_workers=2) as workers:
        results=list(workers.map(perform,[0,1]))
    assert sorted(results)==[200,409]

def test_memory_secrets_and_delay(client,app):
    register(client);a=start(client,'memory')
    assert all(v is None for v in a['state']['board'])
    with app.extensions['db_pool'].connection() as db:
        deck=db.execute('SELECT state FROM attempts WHERE id=%s',(a['id'],)).fetchone()['state']['board']
    i=0;j=next(j for j,v in enumerate(deck) if v!=deck[i]);k=next(k for k in range(16) if k not in (i,j))
    r=api(client,'/api/move',{'attemptId':a['id'],'revision':0,'index':i}).get_json()
    assert sum(v is not None for v in r['attempt']['state']['board'])==1
    api(client,'/api/move',{'attemptId':a['id'],'revision':1,'index':j})
    assert api(client,'/api/move',{'attemptId':a['id'],'revision':2,'index':k}).status_code==400
    app.clock[0]+=1000
    d=client.get('/api/daily?game=memory&difficulty=easy').get_json()
    assert all(v is None for v in d['attempt']['state']['board'])
    assert api(client,'/api/move',{'attemptId':a['id'],'revision':2,'index':k}).status_code==200

def test_midnight_expiration(client,app):
    register(client);a=start(client)
    day=day_key(app.clock[0]);app.clock[0]=reset_at(day)
    assert day_key(app.clock[0])!=day
    assert api(client,'/api/move',{'attemptId':a['id'],'revision':0,'index':0}).status_code==410
    assert start(client)['id']!=a['id']

def test_postgres_persistence_and_idempotent_migrations(client,app):
    register(client);a=start(client)
    migrate(app.config['DATABASE_URL'])
    second=create_app(dict(app.config))
    other=second.test_client();other.set_cookie('pocket_session',client.get_cookie('pocket_session').value)
    assert other.get('/api/daily?game=lights&difficulty=easy').get_json()['attempt']['id']==a['id']
    second.extensions['db_pool'].close()

def test_mobile_assets_and_private_server_files(client):
    assert client.get('/healthz').get_json()['database']=='postgresql'
    for file in ['/','/manifest.webmanifest','/sw.js','/icon-192.png','/icon-512.png','/mobile.js']:
        assert client.get(file).status_code==200
    assert client.get('/.env').status_code==404
    assert client.get('/app.py').status_code==404
    assert client.get('/api/session').headers['Cache-Control']=='no-store'
