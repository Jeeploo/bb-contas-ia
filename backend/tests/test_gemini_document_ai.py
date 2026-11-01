"""SDK Gemini fake: nenhum documento ou credencial enviado à rede."""
import json
import unittest
from types import SimpleNamespace as Obj
from unittest.mock import Mock, patch
import httpx
from google.genai import errors, types
from app.core.config import settings
from app.document_ai.base import DocumentAIError
from app.document_ai.factory import get_document_ai_provider
from app.document_ai.gemini_provider import GeminiDocumentAIProvider
from app.document_ai.openai_provider import OpenAIDocumentAIProvider, schema_leitura
from app.models import Documento, ExtracaoInteligente
from app.schemas.leitura_documental import ContextoDocumental
from app.services.leitura_inteligente import LeituraInteligenteService
from tests.test_document_ai import raw, image_bytes
from tests.test_processamento_documento import pdf, TEXT
from tests import test_validacao_documental as foundation


def response(**fields):
    return Obj(text=json.dumps(raw(**fields)), model_version='modelo-resolvido', response_id='resposta',
               usage_metadata=Obj(prompt_token_count=120, candidates_token_count=40, total_token_count=170),
               candidates=[Obj(finish_reason=types.FinishReason.STOP)])


class GeminiProviderTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.client.models.generate_content.return_value = response()
        self.provider = GeminiDocumentAIProvider(client=self.client, modelo='modelo-configuravel')

    def call(self):
        return self.provider.interpretar_documento(pdf(TEXT), 'application/pdf')

    def test_resolver(self):
        for name, cls in [('openai', OpenAIDocumentAIProvider), ('gemini', GeminiDocumentAIProvider)]:
            with self.subTest(name=name), patch.object(settings, 'document_ai_provider', name):
                self.assertIsInstance(get_document_ai_provider(), cls)
        with patch.object(settings, 'document_ai_provider', 'desconhecido'), self.assertRaises(DocumentAIError) as cm:
            get_document_ai_provider()
        self.assertEqual(cm.exception.codigo, 'document_ai_provider_desconhecido')

    def test_structured_output_pdf_e_usage(self):
        result = self.call()
        args = self.client.models.generate_content.call_args.kwargs
        self.assertEqual(args['model'], 'modelo-configuravel')
        self.assertEqual(args['config'].response_json_schema, schema_leitura())
        self.assertEqual(args['config'].response_mime_type, 'application/json')
        self.assertEqual(args['contents'][0].inline_data.data, pdf(TEXT))
        self.assertEqual(args['contents'][0].inline_data.mime_type, 'application/pdf')
        self.assertEqual(result.metadados['tokens_total'], 170)
        self.assertEqual(result.metadados['tokens_entrada'], 120)
        self.assertEqual(result.metadados['tokens_saida'], 40)
        self.assertGreaterEqual(result.metadados['latencia_ms'], 0)
        self.assertNotIn('id_prefixo', args)
        self.assertNotIn('confianca', result.metadados)

    def test_imagens(self):
        for kind, mime in [('PNG', 'image/png'), ('JPEG', 'image/jpeg')]:
            data = image_bytes(kind)
            self.provider.interpretar_documento(data, mime)
            part = self.client.models.generate_content.call_args.kwargs['contents'][0]
            self.assertEqual(part.inline_data.data, data)
            self.assertEqual(part.inline_data.mime_type, mime)

    def test_sem_usage(self):
        self.client.models.generate_content.return_value.usage_metadata = None
        meta = self.call().metadados
        self.assertIsNone(meta['tokens_total'])
        self.assertIsNone(meta['tokens_entrada'])
        self.assertIsNone(meta['tokens_saida'])

    def test_respostas_invalidas(self):
        for text in ['{', '[]', '{}', json.dumps(raw(valor_total=-1)), json.dumps(raw(tipo_documento='VALIDO')),
                     json.dumps(raw(consumo_kwh=1, consumo_m3=2)), json.dumps(dict.fromkeys(raw()))]:
            with self.subTest(text=text):
                self.client.models.generate_content.return_value.text = text
                with self.assertRaises(DocumentAIError):
                    self.call()

    def test_incompleta_recusa(self):
        for reason in [types.FinishReason.MAX_TOKENS, types.FinishReason.SAFETY]:
            self.client.models.generate_content.return_value.candidates = [Obj(finish_reason=reason)]
            with self.assertRaises(DocumentAIError):
                self.call()

    def test_erros_controlados(self):
        cases = [(httpx.ReadTimeout('segredo'), 'timeout', 504),
                 (httpx.ConnectError('segredo'), 'provider_indisponivel', 503)]
        for status, code, http in [(401,'autenticacao_provider',503), (403,'autenticacao_provider',503),
                (429,'rate_limit',429), (404,'modelo_indisponivel',503), (400,'requisicao_provider_invalida',422),
                (503,'provider_indisponivel',503), (504,'timeout',504)]:
            cases.append((errors.APIError(status, {'error': {'message': 'segredo'}}), code, http))
        cases.append((errors.APIError(400, {'error': {'message': 'response_json_schema inválido'}}), 'schema_invalido', 422))
        for error, code, http in cases:
            with self.subTest(code=code):
                self.client.models.generate_content.side_effect = error
                with self.assertRaises(DocumentAIError) as cm:
                    self.call()
                self.assertEqual((cm.exception.codigo, cm.exception.http_status), (code, http))
                self.assertNotIn('segredo', str(cm.exception.metadados))
                self.assertEqual(cm.exception.metadados['status'], 'erro')

    def test_arquivo_invalido(self):
        with self.assertRaises(DocumentAIError) as cm:
            self.provider.interpretar_documento(b'quebrado', 'application/pdf')
        self.assertEqual(cm.exception.codigo, 'arquivo_invalido')
        self.client.models.generate_content.assert_not_called()

    def test_configuracao_ausente(self):
        with patch.object(settings, 'gemini_api_key', ''), self.assertRaises(DocumentAIError) as cm:
            GeminiDocumentAIProvider().interpretar_documento(image_bytes(), 'image/png')
        self.assertEqual(cm.exception.codigo, 'configuracao_ausente')

    def test_script_generico_gemini_sem_rede(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        import runpy
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / 'conta.png'
            document.write_bytes(image_bytes())
            output = StringIO()
            with patch.object(settings, 'document_ai_provider', 'gemini'), \
                    patch('app.document_ai.gemini_provider.GeminiDocumentAIProvider', return_value=self.provider), \
                    patch.object(sys, 'path', [str(Path('scripts').resolve()), *sys.path]), \
                    patch.object(sys, 'argv', ['scripts/test_document_ai.py', str(document)]), \
                    redirect_stdout(output), self.assertRaises(SystemExit) as cm:
                runpy.run_path('scripts/test_document_ai.py', run_name='__main__')
            self.assertEqual(cm.exception.code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload['metadados']['provider'], 'gemini')
            self.assertEqual(payload['metadados']['tokens_total'], 170)
            self.assertEqual(payload['resultado_documental'], 'EVIDENCIA_INSUFICIENTE')
            self.assertEqual(payload['unidade_consumidora'], '***')

    def test_cliente_oficial_configurado_sem_rede(self):
        with patch.object(settings, 'gemini_api_key', 'fake'), patch('app.document_ai.gemini_provider.genai.Client') as cls:
            cls.return_value.__enter__.return_value = self.client
            GeminiDocumentAIProvider().interpretar_documento(image_bytes(), 'image/png')
            options = cls.call_args.kwargs['http_options']
            self.assertEqual(options.retry_options.attempts, 1)
            self.assertEqual(options.timeout, settings.gemini_document_timeout * 1000)
            cls.return_value.__exit__.assert_called_once()


class GeminiFlowTests(unittest.TestCase):
    def setUp(self):
        foundation.ValidacaoDocumentalTests.setUp(self)
        self.client = Mock()
        self.client.models.generate_content.return_value = response()
        self.storage = Mock()
        self.storage.read.return_value = pdf(TEXT)
        self.service = LeituraInteligenteService(self.s, self.storage,
            GeminiDocumentAIProvider(client=self.client, modelo='modelo-configuravel'))
        self.context = ContextoDocumental(id_usuario=1)

    def test_classificacao_e_validacao(self):
        cases = [({}, 'VALIDO'), ({'tipo_documento':'CONTA_AGUA','consumo_m3':12,'concessionaria':'Empresa 2'}, 'VALIDO'),
                 ({'tipo_documento':'OUTRO'}, 'DOCUMENTO_NAO_SUPORTADO'),
                 ({'uf':None}, 'EVIDENCIA_INSUFICIENTE'),
                 ({'unidade_consumidora':None}, 'EVIDENCIA_INSUFICIENTE'),
                 ({'uf':'BA'}, 'REGIAO_NAO_SUPORTADA')]
        for fields, expected in cases:
            with self.subTest(fields=fields):
                self.client.models.generate_content.return_value = response(**fields)
                result = self.service.processar(1, self.context, reprocessar=True)
                self.assertEqual(result.extracao.resultado_validacao_documental, expected)

    def test_persistencia_original_metadados_idempotencia(self):
        self.client.models.generate_content.return_value = response(uf=' pe ', valor_total='1234.50')
        first = self.service.processar(1, self.context)
        second = self.service.processar(1, self.context)
        self.assertEqual(first.model_dump(), second.model_dump())
        self.client.models.generate_content.assert_called_once()
        extraction = self.s.get(ExtracaoInteligente, first.extracao.id_extracao)
        uf = next(f for f in extraction.dados_extraidos if f.campo_identificado == 'uf')
        self.assertEqual((uf.valor_extraido, uf.valor_normalizado), (' pe ', 'PE'))
        value = next(f for f in extraction.dados_extraidos if f.campo_identificado == 'valor_original')
        self.assertEqual(value.valor_extraido, '1234.50')
        self.assertEqual(extraction.metadados_ia['provider'], 'gemini')
        self.assertEqual(extraction.metadados_ia['modelo'], 'modelo-resolvido')
        self.assertEqual(extraction.metadados_ia['tokens_total'], 170)
        self.assertEqual(extraction.metadados_ia['tokens_entrada'], 120)
        self.assertEqual(extraction.metadados_ia['tokens_saida'], 40)
        self.client.models.generate_content.side_effect = httpx.ReadTimeout('privado')
        with self.assertRaises(DocumentAIError):
            self.service.processar(1, self.context, reprocessar=True)
        self.assertEqual(extraction.resultado_validacao_documental, 'VALIDO')
        self.assertEqual(len(self.s.get(Documento, 1).historico_leitura_ia), 2)
        self.assertEqual(self.s.get(Documento, 1).historico_leitura_ia[-1]['status'], 'erro')
