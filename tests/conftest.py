import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from uuid import uuid4
from pathlib import Path
import psycopg
from psycopg import sql
import pytest
from dotenv import load_dotenv
from app import create_app
from puzzle.migrate import migrate

@pytest.fixture
def app():
    load_dotenv(Path(__file__).resolve().parents[1]/'.env')
    base=os.environ.get('TEST_DATABASE_URL') or os.environ['DATABASE_URL']
    schema='test_'+uuid4().hex
    with psycopg.connect(base) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    parts=urlsplit(base)
    query=dict(parse_qsl(parts.query));query['options']='-csearch_path='+schema
    url=urlunsplit(parts._replace(query=urlencode(query)))
    migrate(url)
    clock=[1790935200000]
    application=create_app({'TESTING':True,'DATABASE_URL':url,'SECRET_KEY':'test-only-secret-'*4,'SESSION_COOKIE_SECURE':False,'NOW':lambda:clock[0]})
    application.clock=clock
    yield application
    application.extensions['db_pool'].close()
    with psycopg.connect(base) as db:
        db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

@pytest.fixture
def client(app):
    return app.test_client()

def api(client,path,data=None,method='POST'):
    csrf=client.get('/api/session').get_json()['csrfToken']
    return client.open(path,method=method,json=data or {},headers={'X-CSRF-Token':csrf,'Origin':'http://localhost'})

def register(client,username='alice'):
    return api(client,'/api/auth/register',{'username':username,'password':'a-test-password-123','name':username.title()})

def start(client,game='lights',difficulty='easy'):
    return api(client,'/api/start',{'game':game,'difficulty':difficulty}).get_json()['attempt']
