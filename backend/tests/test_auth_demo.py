"""Fronteira HTTP real: sem override de identidade, sem IA externa."""
import contextlib
from datetime import timedelta
import io
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.api.auth_dependencies import authorize_request, get_current_user
from app.api.dependencies import get_contexto_operacional
from app import models
from app.models import Usuario, Prefixo, UsuarioPrefixo
from app.models.auth_demo import CredencialDemo, SessaoDemo
from app.services.auth_demo import COOKIE, now, token_hash, verify_secret, hash_secret
from app.services.contexto_operacional import ContextoOperacionalService
from app.schemas.vinculos import UsuarioPrefixoEntrada
from scripts.seed_demo import prepare
from scripts.prepare_demo_auth import provision, PROFILES, demo_access
from tests.test_api import ApiTestCase
from tests.test_document_ai import raw, image_bytes
from app.document_ai.base import InterpretacaoAI
from app.document_ai.normalizacao import normalizar_leitura


class DemoAuthTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        with contextlib.redirect_stdout(io.StringIO()):
            self.manifest=prepare(self.client,'auth')
        config=patch.object(settings,'demo_auth_enabled',True);config.start();self.addCleanup(config.stop)
        self.access={m: {key: value for key, value in values.items() if key != 'perfil'} for m, values in demo_access().items()}
        with Session(self.engine) as session:
            # Fixture reproduz os vínculos já preparados do ambiente de apresentação.
            for matricula, _, codes in PROFILES:
                user = session.query(Usuario).filter_by(matricula=matricula).one()
                entries = [UsuarioPrefixoEntrada(id_prefixo=session.query(Prefixo).filter_by(codigo_prefixo=code).one().id_prefixo, ativo=True, principal=i == 0) for i, code in enumerate(codes)]
                ContextoOperacionalService(session).definir(user.id_usuario, entries)
            provision(session,self.access)
        p=self.manifest['prefixos']['REC-DEMO']['id_prefixo']
        c=self.client.post('/api/v1/contas_consumo',json=dict(numero_conta='AUTH',competencia='2026-09',data_vencimento='2026-10-20',valor_original='736.53',categoria='energia',situacao='pendente',id_prefixo=p,id_concessionaria=self.manifest['concessionarias']['energia']['id_concessionaria'])).json()
        calc=self.client.post('/api/v1/calculos',json=dict(data_calculo='2026-10-06T12:00:00',valor_inicial='736.53',valor_calculado='736.53',situacao='validado',id_conta=c['id_conta'],id_regra=1)).json()
        self.order=self.client.post('/api/v1/ordens_pagamento',json=dict(data_criacao='2026-10-06T12:00:00',data_prevista_pagamento='2026-10-20',valor_total='736.53',situacao='pendente',id_calculo=calc['id_calculo'],id_sistema=1,id_usuario_criador=self.manifest['usuarios']['maker']['id_usuario'])).json()
        for dependency in (authorize_request,get_current_user,get_contexto_operacional):
            app.dependency_overrides.pop(dependency,None)

    def login(self, matricula='DEMO-maker', **changes):
        return self.client.post('/api/v1/auth/login',json=dict(matricula=matricula,senha=changes.get('senha',self.access[matricula]['senha']),segundo_fator=changes.get('segundo_fator',self.access[matricula]['segundo_fator'])))

    def decision(self, **changes):
        return self.client.post('/api/v1/aprovacoes',json=dict(id_ordem=self.order['id_ordem'],decisao='aprovado',data_hora='2026-11-01T12:00:00',**changes))

    def test_cinco_perfis_com_credenciais_simples(self):
        for i, (matricula, _, _) in enumerate(PROFILES, 1):
            with self.subTest(matricula=matricula):
                response = self.login(matricula, senha=str(i), segundo_fator=str(i))
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['usuario']['matricula'], matricula)

    def test_config_e_preparacao_desabilitadas(self):
        self.assertTrue(self.client.get('/api/v1/auth/config').json()['demo_mode'])
        with patch.object(settings, 'demo_auth_enabled', False), Session(self.engine) as session:
            self.assertFalse(self.client.get('/api/v1/auth/config').json()['demo_mode'])
            with self.assertRaises(RuntimeError):
                provision(session)

    def test_login_cookie_persistencia_logout_e_revogacao(self):
        self.assertEqual(self.client.get('/api/v1/contas_consumo').status_code,401)
        response=self.login();self.assertEqual(response.status_code,200,response.text)
        self.assertIn('HttpOnly',response.headers['set-cookie']);self.assertIn('SameSite=strict',response.headers['set-cookie'])
        self.assertNotIn('senha',response.text);self.assertNotIn('token',response.text)
        token=self.client.cookies.get(COOKIE)
        with TestClient(app) as browser:
            browser.cookies.set(COOKIE,token,path='/api/v1')
            self.assertEqual(browser.get('/api/v1/auth/sessao').json(),response.json())
        with Session(self.engine) as session:
            self.assertIsNotNone(session.get(SessaoDemo,token_hash(token)));self.assertIsNone(session.get(SessaoDemo,token))
            credential=session.get(CredencialDemo,response.json()['usuario']['id_usuario'])
            self.assertNotEqual(credential.senha_hash,self.access['DEMO-maker']['senha'])
            self.assertTrue(verify_secret(self.access['DEMO-maker']['senha'],credential.senha_hash))
        self.assertEqual(self.client.post('/api/v1/auth/logout').status_code,204)
        self.client.cookies.set(COOKIE,token,path='/api/v1')
        self.assertEqual(self.client.get('/api/v1/auth/sessao').status_code,401)

    def test_login_invalido_e_erros_sem_segredos(self):
        for changes in (dict(senha='errada'),dict(segundo_fator='errado')):
            self.assertEqual(self.login(**changes).status_code,401)
        self.assertEqual(self.client.post('/api/v1/auth/login',json=dict(matricula='ausente',senha='segredo',segundo_fator='segredo')).status_code,401)
        response=self.client.post('/api/v1/auth/login',json=dict(matricula='DEMO-maker',senha='s'*300,segundo_fator='codigo-secreto'))
        self.assertEqual(response.status_code,422);self.assertNotIn('codigo-secreto',response.text);self.assertNotIn('s'*100,response.text);self.assertNotIn('"input"',response.text)

    def test_expiracao_usuario_inativo_e_feature_desabilitada(self):
        self.login();token=self.client.cookies.get(COOKIE)
        with Session(self.engine) as s:
            s.get(SessaoDemo,token_hash(token)).expira_em=now()-timedelta(seconds=1);s.commit()
        self.assertEqual(self.client.get('/api/v1/auth/sessao').status_code,401)
        self.login()
        with Session(self.engine) as s:
            s.get(Usuario,self.manifest['usuarios']['maker']['id_usuario']).situacao='inativo';s.commit()
        self.assertEqual(self.client.get('/api/v1/auth/sessao').status_code,401)
        with patch.object(settings,'demo_auth_enabled',False):self.assertEqual(self.login().status_code,503)

    def test_prefixo_unico_automatico(self):
        data=self.login().json()
        self.assertEqual([p['codigo_prefixo'] for p in data['prefixos']],['REC-DEMO'])
        self.assertEqual(data['id_prefixo_ativo'],data['id_prefixo_principal'])
        self.assertEqual([p['codigo_prefixo'] for p in self.client.get('/api/v1/prefixos').json()],['REC-DEMO'])
        self.assertEqual(len(self.client.get('/api/v1/usuarios').json()),1)

    def test_multi_prefixo_persistido_e_externo_recusado(self):
        data=self.login('DEMO-maker-multi').json()
        self.assertEqual({p['codigo_prefixo'] for p in data['prefixos']},{'REC-DEMO','PAU-DEMO'})
        paulista=next(p['id_prefixo'] for p in data['prefixos'] if p['codigo_prefixo']=='PAU-DEMO')
        self.assertEqual(self.client.patch('/api/v1/auth/prefixo',json=dict(id_prefixo=paulista)).status_code,200)
        self.assertEqual(self.client.get('/api/v1/auth/sessao').json()['id_prefixo_ativo'],paulista)
        self.assertEqual(self.client.patch('/api/v1/auth/prefixo',json=dict(id_prefixo=999)).status_code,403)
        self.assertEqual(self.client.get('/api/v1/auth/sessao').json()['id_prefixo_ativo'],paulista)

    def test_identidade_forjada_e_edicao_de_privilegios_recusadas(self):
        self.login();other=self.manifest['usuarios']['checker']['id_usuario']
        self.assertEqual(self.decision(id_usuario=other).status_code,403)
        self.assertEqual(self.client.post('/api/v1/documentos/upload',params=dict(id_usuario=other),files={'file':('c.png',image_bytes(),'image/png')}).status_code,403)
        self.assertEqual(self.client.put(f'/api/v1/usuarios/{other}/prefixos',json={'vinculos':[]}).status_code,403)
        self.assertEqual(self.client.patch('/api/v1/usuarios/1',json=dict(id_alcada=999)).status_code,403)
        self.assertEqual(self.client.patch(f"/api/v1/ordens_pagamento/{self.order['id_ordem']}",json=dict(situacao='aprovada')).status_code,403)

    def test_maker_checker_e_alcada(self):
        self.login();self.assertEqual(self.decision().status_code,409)
        self.login('DEMO-limite-baixo');r=self.decision();self.assertEqual(r.status_code,403,r.text);self.assertIn('Alçada',r.text)
        self.login('DEMO-checker');r=self.decision();self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(r.json()['id_usuario'],self.manifest['usuarios']['checker']['id_usuario'])

    def test_processamento_recebe_identidade_da_sessao_e_isola_documentos(self):
        self.login();temp=TemporaryDirectory();self.addCleanup(temp.cleanup)
        original=raw(concessionaria='ENERGIA DEMO PE',unidade_consumidora='UC-REC-ENERGIA-DEMO-001')
        provider=Mock(provider='gemini',modelo='simulado')
        provider.interpretar_documento.return_value=InterpretacaoAI(normalizar_leitura(original),original,dict(status='concluida'))
        with patch.object(settings,'document_storage_path',temp.name),patch('app.services.leitura_inteligente.get_document_ai_provider',return_value=provider):
            r=self.client.post('/api/v1/documentos/upload',files={'file':('c.png',image_bytes(),'image/png')});self.assertEqual(r.status_code,201,r.text)
            id=r.json()['id_documento'];r=self.client.post(f'/api/v1/documentos/{id}/processar-inteligente');self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()['extracao']['id_usuario_contexto'],self.manifest['usuarios']['maker']['id_usuario'])
            self.assertEqual(r.json()['extracao']['id_prefixo_contexto'],self.manifest['prefixos']['REC-DEMO']['id_prefixo'])
            self.login('DEMO-maker-paulista')
            self.assertEqual(self.client.get(f'/api/v1/documentos/{id}').status_code,404)
            self.assertEqual(self.client.post(f'/api/v1/documentos/{id}/processar-inteligente').status_code,404)
            self.assertNotIn(id,[d['id_documento'] for d in self.client.get('/api/v1/documentos').json()]);provider.interpretar_documento.assert_called_once()

    def test_csrf_origem_externa_recusada(self):
        payload=dict(matricula='DEMO-maker',**self.access['DEMO-maker'])
        self.assertEqual(self.client.post('/api/v1/auth/login',headers={'Origin':'https://externo.invalid'},json=payload).status_code,403)
        self.login();self.assertEqual(self.client.post('/api/v1/auth/logout',headers={'Origin':'https://externo.invalid'}).status_code,403)
        self.assertEqual(self.client.get('/api/v1/auth/sessao').status_code,200)

    def test_preparacao_preserva_usuarios_e_hashes(self):
        with Session(self.engine) as s:
            before=[(c.id_usuario,c.senha_hash,c.fator_hash) for c in s.query(CredencialDemo).all()];count=s.query(Usuario).count()
            provision(s,self.access)
            self.assertEqual([(c.id_usuario,c.senha_hash,c.fator_hash) for c in s.query(CredencialDemo).all()],before);self.assertEqual(s.query(Usuario).count(),count)

    def test_preparacao_migra_credenciais_sem_alterar_vinculos_ou_alcadas(self):
        self.login()
        token = self.client.cookies.get(COOKIE)
        with Session(self.engine) as s:
            users = [(u.id_usuario, u.id_alcada, u.id_prefixo) for u in s.query(Usuario).all()]
            links = [(l.id_usuario, l.id_prefixo, l.ativo, l.principal) for l in s.query(UsuarioPrefixo).all()]
            credential = s.get(CredencialDemo, self.manifest['usuarios']['maker']['id_usuario'])
            credential.senha_hash = hash_secret('senha-anterior')
            credential.fator_hash = hash_secret('codigo-anterior')
            s.commit()
            provision(s)
            self.assertIsNone(s.get(SessaoDemo, token_hash(token)))
            self.assertTrue(verify_secret('1', credential.senha_hash))
            self.assertTrue(verify_secret('1', credential.fator_hash))
            self.assertNotEqual(credential.senha_hash, credential.fator_hash)
            self.assertEqual(users, [(u.id_usuario, u.id_alcada, u.id_prefixo) for u in s.query(Usuario).all()])
            self.assertEqual(links, [(l.id_usuario, l.id_prefixo, l.ativo, l.principal) for l in s.query(UsuarioPrefixo).all()])
        self.assertEqual(self.client.get('/api/v1/auth/sessao').status_code, 401)
        self.assertEqual(self.login().status_code, 200)

    def test_ordem_usa_autor_da_sessao_e_recusa_calculo_externo(self):
        self.login()
        data={k:v for k,v in self.order.items() if k not in {'id_ordem','id_usuario_criador'}}
        response=self.client.post('/api/v1/ordens_pagamento',json=data)
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(response.json()['id_usuario_criador'],self.manifest['usuarios']['maker']['id_usuario'])
        data['id_calculo']=self.manifest['ordem']['id_calculo']  # Cadastro legado fora do escopo REC-DEMO.
        import json
        for mime in ('application/json','APPLICATION/JSON','application/vnd.demo+json'):
            with self.subTest(mime=mime):
                response=self.client.post('/api/v1/ordens_pagamento',content=json.dumps(data),headers={'Content-Type':mime})
                self.assertEqual(response.status_code,404,response.text)

    def endpoint(self, id=999):
        return f'/api/v1/extracoes_inteligentes/{id}/resolver-concessionaria'

    def test_exige_sessao(self):
        self.assertEqual(self.client.post(self.endpoint(),json={'id_concessionaria':1}).status_code,401)

    def test_exige_escopo_autorizado(self):
        self.login()
        self.assertEqual(self.client.post(self.endpoint(),json={'id_concessionaria':1}).status_code,404)
        with Session(self.engine) as s:
            for link in s.query(models.UsuarioPrefixo).filter_by(id_usuario=self.manifest['usuarios']['maker']['id_usuario']): link.ativo=False; link.principal=False
            s.commit()
        self.assertEqual(self.client.post(self.endpoint(),json={'id_concessionaria':1}).status_code,403)

    def test_listagem_minima_ativa(self):
        self.login()
        response=self.client.get('/api/v1/concessionarias/elegiveis/associacao')
        self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(response.json())
        self.assertEqual(set(response.json()[0]),{'id_concessionaria','nome','ativo'})

    def test_identidade_frontend_recusada(self):
        self.login()
        self.assertEqual(self.client.post(self.endpoint(self.persisted_extraction()),json={'id_concessionaria':1,'id_usuario':999}).status_code,403)


    def persisted_extraction(self):
        from datetime import datetime
        with Session(self.engine) as s:
            p = self.manifest['prefixos']['REC-DEMO']['id_prefixo']
            doc = models.Documento(tipo_documento='fatura', formato='pdf', data_recebimento=datetime.now(),
                origem='snapshot', caminho_arquivo='001763932016.pdf', id_prefixo_contexto=p)
            s.add(doc); s.flush()
            e = models.ExtracaoInteligente(id_documento=doc.id_documento, data_processamento=datetime.now(),
                situacao_validacao='revisao_cadastral_pendente', id_usuario_contexto=self.manifest['usuarios']['maker']['id_usuario'],
                id_prefixo_contexto=p)
            s.add(e); s.flush()
            values = dict(tipo_documento='ENERGIA', uf='PE', municipio='Recife',
                concessionaria='COMPANHIA ENERGÉTICA DE PERNAMBUCO', unidade_consumidora='001',
                competencia='2026-09', data_vencimento='2026-10-20', valor_original='736.53')
            for name, value in values.items():
                s.add(models.DadoExtraido(id_extracao=e.id_extracao,campo_identificado=name,
                    valor_extraido=value,valor_validado=value,situacao_validacao='validada'))
            s.commit()
            return e.id_extracao

    def test_associacao_http_identidade_sessao_sem_ia(self):
        user = self.login().json()['usuario']['id_usuario']
        eid = self.persisted_extraction()
        cid = self.manifest['concessionarias']['energia']['id_concessionaria']
        with patch('app.services.leitura_inteligente.get_document_ai_provider',side_effect=AssertionError('IA proibida')):
            response = self.client.post(self.endpoint(eid),json={'id_concessionaria':cid})
        self.assertEqual(response.status_code,200,response.text)
        e = response.json()
        self.assertEqual(e['evidencias_validacao_documental']['id_concessionaria'],cid)
        audit = next(h for h in e['historico_validacao_documental'] if h.get('evento')=='CONCESSIONARIA_ASSOCIADA')
        self.assertEqual(audit['id_usuario'],user)
        self.assertEqual(audit['nome_extraido'],'COMPANHIA ENERGÉTICA DE PERNAMBUCO')
        with Session(self.engine) as s:
            self.assertEqual(s.query(models.ConcessionariaAlias).count(),1)

    def test_associacao_http_inexistente_e_identidade_extra(self):
        user = self.login().json()['usuario']['id_usuario']
        eid = self.persisted_extraction()
        response = self.client.post(self.endpoint(eid),json={'id_concessionaria':999999})
        self.assertEqual(response.status_code,403,response.text)
        response = self.client.post(self.endpoint(eid),json={'id_concessionaria':1,'id_usuario':user})
        self.assertEqual(response.status_code,422,response.text)
