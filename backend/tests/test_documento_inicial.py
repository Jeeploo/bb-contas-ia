"""Documento primeiro: integração sem conta prévia e sem rede."""
from tests import test_document_ai_api as foundation
from tests.test_api import ApiTestCase
from tests.test_document_ai import raw, image_bytes
from app.document_ai.base import InterpretacaoAI
from app.document_ai.normalizacao import normalizar_leitura


class DocumentoInicialTests(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        from tests.test_api import ENTITIES
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock, patch
        from app.core.config import settings
        for resource, _, payload, _ in ENTITIES[:5]:
            self.client.post('/api/v1/'+resource, json=payload)
        self.client.post('/api/v1/usuarios',json=dict(matricula='U',nome='Operador',funcao='operador',situacao='ativo',id_prefixo=1))
        self.client.post('/api/v1/unidades_consumidoras',json=dict(id_prefixo=1,id_concessionaria=1,unidade_consumidora='001'))
        directory = TemporaryDirectory(); self.addCleanup(directory.cleanup)
        storage = patch.object(settings,'document_storage_path',directory.name)
        storage.start(); self.addCleanup(storage.stop)
        self.provider = Mock(provider='gemini',modelo='teste')
        adapter = patch('app.services.leitura_inteligente.get_document_ai_provider',return_value=self.provider)
        adapter.start(); self.addCleanup(adapter.stop)

    processar = foundation.AIEndpointTests.processar
    def upload(self, **params):
        response = self.client.post('/api/v1/documentos/upload', params=dict(id_usuario=1, **params),
            files={'file': ('fatura.png', image_bytes(), 'image/png')})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNone(response.json()['id_conta'])
        return response.json()['id_documento']

    def configure(self, **changes):
        original = raw(concessionaria='Teste', competencia='09/2026', valor_total='736,53',
                       data_vencimento='20/10/2026', consumo_kwh='523', codigo_barras='8'*48)
        original.update(changes)
        self.provider.interpretar_documento.return_value = InterpretacaoAI(normalizar_leitura(original), original, dict(status='concluida'))

    def test_cria_conta_da_leitura_idempotente(self):
        # Remove a conta da fixture: não há conta de referência disponível.
        self.client.delete('/api/v1/documentos/1')
        self.client.delete('/api/v1/contas_consumo/1')
        self.assertEqual(self.client.get('/api/v1/contas_consumo').json(), [])
        self.configure()
        id = self.upload()
        response = self.processar(id)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        fields = {f['campo_identificado']:f for f in data['campos_encontrados']}
        self.assertEqual(fields['competencia']['valor_extraido'], '09/2026')
        self.assertEqual(fields['competencia']['valor_normalizado'], '2026-09')
        self.assertEqual(fields['valor_original']['valor_normalizado'], '736.53')
        self.assertEqual(fields['unidade_consumidora']['valor_extraido'], '001')
        self.assertEqual(fields['codigo_barras']['valor_normalizado'], '8'*48)
        self.assertEqual(fields['consumo']['valor_normalizado'], '523')
        account = self.client.get('/api/v1/contas_consumo').json()[0]
        self.assertEqual(account['competencia'], '2026-09')
        self.assertEqual(account['valor_original'], '736.53')
        self.assertEqual(account['numero_conta'], '001')
        self.assertEqual(self.processar(id).json(), data)
        self.provider.interpretar_documento.assert_called_once()
        self.client.post(f'/api/v1/documentos/{id}/processar-inteligente', params=dict(id_usuario=1,reprocessar=True))
        self.assertEqual(len(self.client.get('/api/v1/contas_consumo').json()), 1)

    def test_decisoes_sem_inventar_conta(self):
        for changes, expected in [({'tipo_documento':'OUTRO'}, 'DOCUMENTO_NAO_SUPORTADO'),
            ({'uf':'SP'}, 'REGIAO_NAO_SUPORTADA'),
            ({'concessionaria':'Concessionária real sem cadastro'}, 'VALIDO'),
            ({'municipio':'Olinda'}, 'DIVERGENCIA_PREFIXO')]:
            with self.subTest(expected=expected):
                self.configure(**changes)
                result = self.processar(self.upload()).json()
                self.assertEqual(result['extracao']['resultado_validacao_documental'], expected)
                self.assertIsNone(result['documento']['id_conta'])
                if 'concessionaria' in changes:
                    field = next(f for f in result['campos_encontrados'] if f['campo_identificado']=='concessionaria')
                    self.assertEqual(field['valor_extraido'], changes['concessionaria'])

    def test_um_prefixo_automatico_varios_exigem_selecao(self):
        from tests.test_api import ENTITIES
        self.upload()  # Único vínculo: seleção automática pelo backend.
        self.client.post('/api/v1/prefixos', json={**ENTITIES[1][2], 'codigo_prefixo':'OUTRO'})
        self.client.put('/api/v1/usuarios/1/prefixos', json={'vinculos':[
            dict(id_prefixo=1,ativo=True,principal=True),dict(id_prefixo=2,ativo=True,principal=False)]})
        files={'file':('fatura.png',image_bytes(),'image/png')}
        response=self.client.post('/api/v1/documentos/upload',params=dict(id_usuario=1),files=files)
        self.assertEqual(response.status_code,403)
        self.upload(id_prefixo=1)
        response=self.client.post('/api/v1/documentos/upload',params=dict(id_usuario=1,id_prefixo=99),files=files)
        self.assertEqual(response.status_code,403)

    def test_correcao_preserva_original_e_cria_conta_quando_resolvida(self):
        self.configure(concessionaria='Nome real sem correspondência')
        id=self.upload()
        result=self.processar(id).json()
        field=next(f for f in result['campos_encontrados'] if f['campo_identificado']=='concessionaria')
        self.assertIsNone(result['documento']['id_conta'])
        response=self.client.patch(f"/api/v1/dados_extraidos/{field['id_dado_extraido']}/validacao",json=dict(valor_validado='Teste'))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['valor_extraido'],'Nome real sem correspondência')
        self.assertEqual(response.json()['valor_validado'],'Teste')
        document=self.client.get(f'/api/v1/documentos/{id}').json()
        self.assertIsNotNone(document['id_conta'])

    def test_validacao_competencia_canonica_preserva_original(self):
        self.configure()
        id=self.upload()
        result=self.processar(id).json()
        field=next(f for f in result['campos_encontrados'] if f['campo_identificado']=='competencia')
        url=f"/api/v1/dados_extraidos/{field['id_dado_extraido']}/validacao"
        self.assertEqual(self.client.patch(url,json=dict(valor_validado='09/2026')).status_code,422)
        response=self.client.patch(url,json=dict(valor_validado='2026-09'))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['valor_extraido'],'09/2026')
        self.assertEqual(response.json()['valor_validado'],'2026-09')

    def test_envio_cadastral_preserva_documento_sem_bloquear_calculo(self):
        nome = 'COMPANHIA ENERGÉTICA DE PERNAMBUCO'
        self.configure(concessionaria=nome)
        result = self.processar(self.upload()).json()
        ext = result['extracao']
        self.assertTrue(ext['permite_envio_validacao'])
        self.assertEqual(ext['pendencias'][0]['tipo'], 'CORRESPONDENCIA_CONCESSIONARIA')
        for field in result['campos_encontrados']:
            response = self.client.patch(f"/api/v1/dados_extraidos/{field['id_dado_extraido']}/validacao", json={})
            self.assertEqual(response.status_code, 200, response.text)
        response = self.client.post(f"/api/v1/extracoes_inteligentes/{ext['id_extracao']}/enviar-validacao")
        self.assertEqual(response.status_code, 200, response.text)
        sent = response.json()
        self.assertEqual(sent['situacao_validacao'], 'validada')
        self.assertEqual(sent['resultado_validacao_documental'], 'VALIDO')
        self.assertFalse(sent['bloqueia_calculo'])
        self.assertIsNone(sent['evidencias_validacao_documental'].get('id_concessionaria'))
        self.assertEqual(sent['historico_validacao_documental'][-1]['evento'], 'ENVIADO_PARA_VALIDACAO')
        fields = self.client.get('/api/v1/dados_extraidos').json()
        field = next(f for f in fields if f['id_extracao']==ext['id_extracao'] and f['campo_identificado']=='concessionaria')
        self.assertEqual(field['valor_extraido'], nome)
        self.assertEqual(field['valor_validado'], nome)
        doc = self.client.get(f"/api/v1/documentos/{result['documento']['id_documento']}").json()
        self.assertIsNone(doc['id_conta'])
        self.provider.interpretar_documento.assert_called_once()
    def test_envio_bloqueado_por_impedimentos_documentais(self):
        for changes in ({'tipo_documento':'OUTRO'}, {'uf':'SP'},
                        {'concessionaria':'Sem cadastro', 'unidade_consumidora':None},
                        {'concessionaria':'Sem cadastro', 'valor_total':None},
                        {'concessionaria':'Sem cadastro', 'competencia':None}):
            with self.subTest(changes=changes):
                self.configure(**changes)
                ext = self.processar(self.upload()).json()['extracao']
                self.assertFalse(ext['permite_envio_validacao'])
                response = self.client.post(f"/api/v1/extracoes_inteligentes/{ext['id_extracao']}/enviar-validacao")
                self.assertEqual(response.status_code, 403, response.text)

    def test_envio_exige_confirmacao_documental(self):
        self.configure(concessionaria='Sem cadastro')
        ext = self.processar(self.upload()).json()['extracao']
        response = self.client.post(f"/api/v1/extracoes_inteligentes/{ext['id_extracao']}/enviar-validacao")
        self.assertEqual(response.status_code, 403)
        self.assertIn('Confirme os dados', response.json()['detail'])
