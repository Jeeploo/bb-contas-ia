"""Configuração e hosting sem recursos externos, rede ou chamadas de IA."""
import contextlib
import io
import json
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import Settings, settings
from app.main import app, create_app
from app.api.db_dependency import get_db
from app.api.auth_dependencies import authorize_request, get_current_user
from app.api.dependencies import get_contexto_operacional
from app.services.login_rate_limit import LoginRateLimiter
from app.services.auth_demo import hash_secret
from app.models.auth_demo import CredencialDemo
from tests.test_api import ApiTestCase, ENTITIES


def external(**changes):
    return dict(APP_ENV='homologation', DEMO_MODE='true', FRONTEND_ORIGIN='https://app.exemplo.com',
        DATABASE_URL='postgresql://user:password@pg.exemplo.com/demo?sslmode=require',
        DOCUMENT_STORAGE_PATH='/data/documentos', DOCUMENT_STORAGE_PERSISTENT='true', **changes)


class DeployConfigTests(unittest.TestCase):
    def test_defaults_local_demo_opt_in(self):
        config=Settings({})
        self.assertEqual(config.port,8000)
        self.assertFalse(config.demo_auth_enabled)
        self.assertFalse(config.demo_cookie_secure)
        self.assertEqual(config.allowed_origins,['http://127.0.0.1:5173','http://localhost:5173'])
        self.assertTrue(Settings({'DEMO_MODE':'true'}).demo_auth_enabled)
        self.assertFalse(Settings({'DEMO_MODE':'false','DEMO_AUTH_ENABLED':'true'}).demo_auth_enabled)

    def test_external_origin_exclusiva_e_postgres(self):
        config=Settings(external())
        self.assertTrue(config.demo_cookie_secure)
        self.assertEqual(config.allowed_origins,['https://app.exemplo.com'])
        self.assertEqual(config.database_url,'postgresql+psycopg://user:password@pg.exemplo.com/demo?sslmode=require')
        for prefix in ('postgres://','postgresql://','postgresql+psycopg://'):
            data=external();data['DATABASE_URL']=prefix+'u:p@db.example/demo?sslmode=require'
            self.assertTrue(Settings(data).database_url.startswith('postgresql+psycopg://'))

    def test_external_config_fails_closed(self):
        for changes in [dict(FRONTEND_ORIGIN='*'),dict(FRONTEND_ORIGIN='http://app.exemplo.com'),
            dict(FRONTEND_ORIGIN='https://app.exemplo.com/path'),dict(FRONTEND_ORIGIN='https://app.exemplo.com,https://other.example'),
            dict(SESSION_COOKIE_SECURE='false'),dict(DATABASE_URL='sqlite://'),
            dict(DATABASE_URL='postgresql://u:segredo@localhost/db'),dict(DOCUMENT_STORAGE_PERSISTENT='false'),
            dict(DOCUMENT_STORAGE_PATH='./uploads'),dict(DOCUMENT_STORAGE_BACKEND='s3')]:
            data=external();data.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError) as err:
                Settings(data)
            self.assertNotIn('segredo',str(err.exception))

    def test_same_site_none_requires_secure(self):
        self.assertEqual(Settings({'SESSION_COOKIE_SECURE':'true','SESSION_COOKIE_SAMESITE':'None'}).session_cookie_samesite,'none')
        for data in [dict(SESSION_COOKIE_SAMESITE='none'),dict(SESSION_COOKIE_SAMESITE='invalid'),dict(SESSION_TTL='0')]:
            with self.assertRaises(ValueError):Settings(data)

    def test_port_start_command_and_validation(self):
        from app.start import command
        with patch.object(settings,'port',8765):
            args=command()
            self.assertEqual(args[args.index('--port')+1],'8765')
            self.assertEqual(args[args.index('--host')+1],'0.0.0.0')
            self.assertIn('--no-access-log',args)
            self.assertNotIn('alembic',args)
        for value in ('0','-1','65536','abc'):
            with self.assertRaises(ValueError):Settings({'PORT':value})

    def test_cors_por_ambiente_e_preflight_com_cookie(self):
        for config,allowed,denied in [(Settings({}),'http://127.0.0.1:5173','https://externo.example'),
                                     (Settings(external()),'https://app.exemplo.com','http://localhost:5173')]:
            with patch.dict(settings.__dict__,config.__dict__,clear=True):
                with TestClient(create_app()) as client:
                    request_headers={'Origin':allowed,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
                    response=client.options('/api/v1/auth/login',headers=request_headers)
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(response.headers['access-control-allow-origin'],allowed)
                    self.assertEqual(response.headers['access-control-allow-credentials'],'true')
                    request_headers['Origin']=denied
                    response=client.options('/api/v1/auth/login',headers=request_headers)
                    self.assertEqual(response.status_code,400)
                    self.assertNotIn('access-control-allow-origin',response.headers)

    def test_health_sem_dados_sensiveis_quando_banco_cai(self):
        with TestClient(app) as client:
            with patch('app.main.test_database_connection',return_value=1):
                response=client.get('/health');self.assertEqual(response.status_code,200)
                self.assertEqual(response.json(),{'status':'ok','database':'connected'})
            with patch('app.main.test_database_connection',side_effect=RuntimeError('postgres://secret@host;PDF,UC,cookie')):
                with self.assertLogs('app.main',level='WARNING') as logs:
                    response=client.get('/health')
                self.assertEqual(response.status_code,503)
                self.assertEqual(response.json(),{'status':'ok','database':'error'})
                self.assertNotIn('secret',response.text+' '.join(logs.output))

    def test_erros_e_logs_externos_nao_serializam_valores(self):
        config=Settings(external())
        with patch.dict(settings.__dict__,config.__dict__,clear=True):
            application=create_app()
            @application.get('/test-error')
            def fail():raise RuntimeError('APIKEY senha COOKIE PDF UC1234-78 83600000000000')
            with TestClient(application) as client,self.assertLogs('app.main',level='ERROR') as logs:
                response=client.get('/test-error?token=secreto',headers={'Origin':'https://app.exemplo.com'})
            self.assertEqual(response.status_code,500)
            self.assertEqual(response.headers['access-control-allow-origin'],'https://app.exemplo.com')
            for secret in ('APIKEY','senha','COOKIE','PDF','UC1234-78','83600000000000','secreto'):
                self.assertNotIn(secret,response.text+' '.join(logs.output))

    def test_limiter_bloqueia_expira_e_nao_armazena_identificador(self):
        clock=[0.0];limiter=LoginRateLimiter(clock=lambda:clock[0])
        for _ in range(2):limiter.failure('ip','matricula-inexistente',2,10,20)
        self.assertEqual(limiter.retry_after('ip','outra',10),20)
        self.assertEqual(limiter.retry_after('outro-ip','matricula-inexistente',10),20)
        self.assertNotIn('matricula-inexistente',str(limiter.entries))
        clock[0]=11;self.assertEqual(limiter.retry_after('ip','matricula-inexistente',10),9)
        clock[0]=21;self.assertEqual(limiter.retry_after('ip','matricula-inexistente',10),0)
        limiter.failure('ip','matricula',2,10,20)
        clock[0]=32;self.assertEqual(limiter.retry_after('ip','matricula',10),0)
        self.assertEqual(limiter.entries,{})
        bounded=LoginRateLimiter(clock=lambda:0,max_entries=2)
        bounded.failure('ip','user',1,10,20)
        self.assertGreater(bounded.retry_after('new-ip','new-user',10),0)
        self.assertEqual(len(bounded.entries),2)


class DeployAuthTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        for resource,_,payload,_ in ENTITIES[:3]:self.client.post('/api/v1/'+resource,json=payload)
        self.client.post('/api/v1/usuarios',json=dict(matricula='DEMO',nome='Demo',funcao='maker',situacao='ativo',id_prefixo=1))
        with Session(self.engine) as session:
            session.add(CredencialDemo(id_usuario=1,senha_hash=hash_secret('somente-teste'),fator_hash=hash_secret('123456')));session.commit()
        for dependency in (authorize_request,get_current_user,get_contexto_operacional):app.dependency_overrides.pop(dependency,None)
        config=patch.object(settings,'demo_auth_enabled',True);config.start();self.addCleanup(config.stop)
        old=app.state.login_limiter;app.state.login_limiter=LoginRateLimiter()
        self.addCleanup(setattr,app.state,'login_limiter',old)

    def login(self,client=None,**changes):
        return (client or self.client).post('/api/v1/auth/login',json=dict(matricula=changes.get('matricula','DEMO'),senha=changes.get('senha','somente-teste'),segundo_fator='123456'))

    def test_cookie_secure_samesite_e_ttl_configuraveis(self):
        config=Settings(external(SESSION_COOKIE_SAMESITE='none',SESSION_TTL='123'))
        with patch.dict(settings.__dict__,config.__dict__,clear=True):
            application=create_app();application.dependency_overrides[get_db]=app.dependency_overrides[get_db]
            with TestClient(application,base_url='https://api.exemplo.com') as client:
                response=self.login(client)
                self.assertEqual(response.status_code,200,response.text)
                cookie=response.headers['set-cookie']
                for expected in ('Secure','HttpOnly','SameSite=none','Max-Age=123'):self.assertIn(expected,cookie)
                self.assertEqual(client.get('/api/v1/auth/sessao').status_code,200)
                self.assertIn('SameSite=none',client.post('/api/v1/auth/logout').headers['set-cookie'])

    def test_rate_limit_generico_sem_enumeracao_e_retry(self):
        clock=[0.0];app.state.login_limiter=LoginRateLimiter(clock=lambda:clock[0])
        with patch.object(settings,'login_max_attempts',2),patch.object(settings,'login_window_seconds',10),patch.object(settings,'login_block_seconds',20):
            first=self.login(senha='errada');second=self.login(matricula='ausente')
            self.assertEqual(first.status_code,401);self.assertEqual(second.status_code,401)
            self.assertEqual(first.json(),second.json())
            blocked=self.login();self.assertEqual(blocked.status_code,429)
            self.assertEqual(blocked.headers['retry-after'],'20')
            self.assertEqual(self.login(matricula='ausente').json(),blocked.json())
            clock[0]=21;self.assertEqual(self.login().status_code,200)

    def test_forwarded_for_nao_contorna_limiter_sem_proxy_confiavel(self):
        with patch.object(settings,'login_max_attempts',1):
            response=self.client.post('/api/v1/auth/login',headers={'X-Forwarded-For':'1.2.3.4'},json=dict(matricula='ausente',senha='errada',segundo_fator='000000'))
            self.assertEqual(response.status_code,401)
            response=self.client.post('/api/v1/auth/login',headers={'X-Forwarded-For':'9.8.7.6'},json=dict(matricula='DEMO',senha='somente-teste',segundo_fator='123456'))
            self.assertEqual(response.status_code,429)


class MaintenanceSeedTests(ApiTestCase):
    def test_seed_offline_sem_backend_sem_rede_e_idempotente(self):
        from scripts.seed_demo import prepare
        from scripts.seed_client import MaintenanceSeedClient
        from app.models import Base
        with Session(self.engine) as session,patch('socket.socket.connect',side_effect=AssertionError('Rede proibida')),contextlib.redirect_stdout(io.StringIO()):
            client=MaintenanceSeedClient(session)
            first=prepare(client,'offline')
            before={t.name:[dict(r) for r in session.execute(t.select()).mappings()] for t in Base.metadata.sorted_tables}
            self.assertEqual(prepare(client,'offline'),first)
            after={t.name:[dict(r) for r in session.execute(t.select()).mappings()] for t in Base.metadata.sorted_tables}
            self.assertEqual(before,after)

    def test_cli_seed_e_credenciais_exigem_modo_demo(self):
        from scripts.seed_demo import main as seed_main
        from scripts.prepare_demo_auth import main as auth_main
        with patch.object(settings,'demo_auth_enabled',False),contextlib.redirect_stderr(io.StringIO()):
            with patch('sys.argv',['seed_demo.py','--ambiente-demo']),self.assertRaises(SystemExit) as error:seed_main()
            self.assertEqual(error.exception.code,2)
            with TemporaryDirectory() as folder,patch('sys.argv',['prepare_demo_auth.py','--ambiente-demo','--arquivo',folder+'/access.json']),self.assertRaises(SystemExit) as error:auth_main()
            self.assertEqual(error.exception.code,2)
