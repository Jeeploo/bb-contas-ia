from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch
from tests.test_api import ApiTestCase, ENTITIES
from tests.test_document_ai import raw, image_bytes
from app.core.config import settings
from app.document_ai.base import InterpretacaoAI, DocumentAIError
from app.document_ai.normalizacao import normalizar_leitura


class AIEndpointTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        for resource, _, payload, _ in ENTITIES[:5]:
            self.assertEqual(self.client.post('/api/v1/'+resource,json=payload).status_code,201)
        self.assertEqual(self.client.post('/api/v1/usuarios',json=dict(matricula='U',nome='Operador',funcao='operador',situacao='ativo',id_prefixo=1)).status_code,201)
        self.assertEqual(self.client.post('/api/v1/unidades_consumidoras',json=dict(id_prefixo=1,id_concessionaria=1,unidade_consumidora='001')).status_code,201)
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        config=patch.object(settings,'document_storage_path',temp.name)
        config.start()
        self.addCleanup(config.stop)
        self.provider=Mock(provider='openai',modelo='modelo-teste')
        original=raw(concessionaria='Teste')
        self.provider.interpretar_documento.return_value=InterpretacaoAI(normalizar_leitura(original),original,
            dict(provider='openai',modelo='modelo-teste',tokens_entrada=50,tokens_saida=20,status='concluida'))
        adapter=patch('app.services.leitura_inteligente.get_document_ai_provider',return_value=self.provider)
        adapter.start()
        self.addCleanup(adapter.stop)

    def upload(self,filename='conta.png',mime='image/png',data=None):
        response=self.client.post('/api/v1/contas_consumo/1/documentos/upload',
            params=dict(id_usuario=1),files={'file':(filename,image_bytes() if data is None else data,mime)})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()['id_documento']

    def processar(self,document_id):
        return self.client.post(f'/api/v1/documentos/{document_id}/processar-inteligente',params=dict(id_usuario=1))

    def test_endpoint_integra_provider_e_validador(self):
        document_id=self.upload()
        response=self.processar(document_id)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['extracao']['resultado_validacao_documental'],'VALIDO')
        self.assertEqual(response.json()['metadados_ia']['tokens_entrada'],50)
        self.assertEqual(self.provider.interpretar_documento.call_args.args[1],'image/png')

    def test_jpg_e_jpeg(self):
        for extension in ('jpg','jpeg'):
            document_id=self.upload(filename='conta.'+extension,mime='image/jpeg',data=image_bytes('JPEG'))
            response=self.processar(document_id)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(self.provider.interpretar_documento.call_args.args[1],'image/jpeg')

    def test_mime_incompativel_rejeitado(self):
        response=self.client.post('/api/v1/contas_consumo/1/documentos/upload',files={'file':('conta.png',image_bytes(),'image/jpeg')})
        self.assertEqual(response.status_code,415,response.text)
        self.provider.interpretar_documento.assert_not_called()

    def test_idempotencia_endpoint(self):
        document_id=self.upload()
        first=self.processar(document_id)
        second=self.processar(document_id)
        self.assertEqual(first.json(),second.json())
        self.provider.interpretar_documento.assert_called_once()

    def test_erros_http_sem_dados_sensiveis(self):
        document_id=self.upload()
        for code,status in [('timeout',504),('rate_limit',429),('autenticacao_provider',503),('resposta_invalida',502)]:
            self.provider.interpretar_documento.side_effect=DocumentAIError(code,status)
            with self.subTest(code=code):
                response=self.processar(document_id)
                self.assertEqual(response.status_code,status,response.text)
                self.assertEqual(response.json(),{'detail':{'codigo':code}})
                self.assertEqual(self.client.get('/api/v1/extracoes_inteligentes').json(),[])
        history=self.client.get(f'/api/v1/documentos/{document_id}/leituras-ia',params=dict(id_usuario=1))
        self.assertEqual(history.status_code,200,history.text)
        self.assertEqual(len(history.json()['tentativas']),4)

    def test_contexto_obrigatorio(self):
        document_id=self.upload()
        response=self.client.post(f'/api/v1/documentos/{document_id}/processar-inteligente')
        self.assertEqual(response.status_code,403,response.text)
        self.provider.interpretar_documento.assert_not_called()

    def test_script_manual_sem_rede_mascara_identificadores(self):
        script=Path('scripts/test_openai_document.py')
        spec=importlib.util.spec_from_file_location('manual_openai_document',script)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            document=Path(directory)/'conta.png'
            document.write_bytes(image_bytes())
            report=Path(directory)/'relatorio.json'
            output,errors=StringIO(),StringIO()
            with patch.object(module,'get_document_ai_provider',return_value=self.provider), patch('sys.argv',[str(script),str(document),'--relatorio',str(report)]),redirect_stdout(output),redirect_stderr(errors):
                self.assertEqual(module.main(),0,errors.getvalue())
            payload=json.loads(output.getvalue())
            self.assertEqual(payload['unidade_consumidora'],'***')
            self.assertNotIn('codigo_barras',payload)
            self.assertEqual(json.loads(report.read_text())['extraido']['unidade_consumidora'],'001')
            self.assertEqual(report.stat().st_mode & 0o777,0o600)
