"""PDFs em memória, SQLite e storage temporário; nenhum acesso à rede."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from decimal import Decimal
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from tests.test_api import ApiTestCase, ENTITIES
from app.core.config import settings
from app.models import Documento, ExtracaoInteligente, DadoExtraido
from app.processing.fields import DeterministicFieldExtractor
from app.processing.text import PdfTextExtractor
from app.services.processamento_documento import ProcessamentoDocumentoService

TEXT = ('Valor total: R$ 123,45\nVencimento: 20/10/2026\nConsumo: 100,500 kWh\n'
        'Competência: 10/2026\nCódigo de barras: ' + '1' * 44)


def pdf(text=None):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    if text is not None:
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica'),
            NameObject('/Encoding'): NameObject('/WinAnsiEncoding')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        commands = ['BT /F1 12 Tf 40 740 Td 16 TL']
        for line in text.splitlines():
            escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append(f'({escaped}) Tj T*')
        commands.append('ET')
        stream.set_data('\n'.join(commands).encode('cp1252'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class DocumentFlowTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.storage = Path(temp.name) / 'documents'
        config = patch.object(settings, 'document_storage_path', str(self.storage))
        config.start()
        self.addCleanup(config.stop)
        for resource, _, payload, _ in ENTITIES[:4]:
            response = self.client.post('/api/v1/' + resource, json=payload)
            self.assertEqual(response.status_code, 201, response.text)

    def upload(self, data=None, name='fatura.pdf', mime='application/pdf', account=1):
        return self.client.post(f'/api/v1/contas_consumo/{account}/documentos/upload',
            files={'file': (name, pdf(TEXT) if data is None else data, mime)})

    def process(self, document=1):
        return self.client.post(f'/api/v1/documentos/{document}/processar')

    def prepared(self):
        self.assertEqual(self.upload().status_code, 201)
        response = self.process()
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_upload_valid(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.text)
        doc = response.json()
        self.assertEqual(doc['id_conta'], 1)
        self.assertEqual((self.storage / doc['caminho_arquivo']).read_bytes(), pdf(TEXT))

    def test_missing_account(self):
        self.assertEqual(self.upload(account=999).status_code, 404)
        self.assertFalse(self.storage.exists())

    def test_empty(self):
        self.assertEqual(self.upload(data=b'').status_code, 400)
        self.assertFalse(self.storage.exists())

    def test_unsupported_format(self):
        for name, mime in [('file.txt', 'application/pdf'), ('file.pdf', 'text/plain')]:
            self.assertEqual(self.upload(name=name, mime=mime).status_code, 415)

    def test_oversized(self):
        with patch.object(settings, 'document_max_size_bytes', 64):
            self.assertEqual(self.upload().status_code, 413)
        self.assertFalse(self.storage.exists())

    def test_malicious_filename(self):
        response = self.upload(name='../../escaped.pdf')
        self.assertEqual(response.status_code, 201, response.text)
        key = response.json()['caminho_arquivo']
        self.assertEqual(Path(key).name, key)
        self.assertEqual(len(key), 36)
        self.assertEqual(list(self.storage.parent.rglob('*.pdf')), [self.storage / key])

    def test_fake_pdf(self):
        self.assertEqual(self.upload(data=b'not pdf').status_code, 400)

    def test_processing_textual_pdf(self):
        result = self.prepared()
        fields = {f['campo_identificado']: f['valor_extraido'] for f in result['campos_encontrados']}
        self.assertEqual(fields, dict(valor_original='123.45', data_vencimento='2026-10-20',
            consumo='100.500', competencia='2026-10', codigo_barras='1' * 44))
        self.assertNotIn('texto', result)
        self.assertEqual(result['situacao'], 'requer_validacao')

    def test_extraction_persisted(self):
        result = self.prepared()
        self.assertEqual(self.client.get('/api/v1/extracoes_inteligentes').json(), [result['extracao']])

    def test_fields_persisted(self):
        result = self.prepared()
        self.assertEqual(self.client.get('/api/v1/dados_extraidos').json(), result['campos_encontrados'])
        self.assertTrue(all(f['situacao_validacao'] == 'pendente' for f in result['campos_encontrados']))

    def test_confidence(self):
        result = self.prepared()
        confidences = [Decimal(f['nivel_confianca']) for f in result['campos_encontrados']]
        self.assertTrue(all(0 <= c <= 100 for c in confidences))
        self.assertEqual(Decimal(result['confianca_geral']), sum(confidences) / len(confidences))

    def test_no_text_requires_ocr(self):
        self.assertEqual(self.upload(data=pdf()).status_code, 201)
        response = self.process()
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn('OCR', response.json()['detail'])
        self.assertEqual(self.client.get('/api/v1/extracoes_inteligentes').json(), [])
        self.assertEqual(len(self.client.get('/api/v1/documentos').json()), 1)

    def test_missing_document(self):
        self.assertEqual(self.process(999).status_code, 404)

    def test_duplicate_processing_reuses_extraction(self):
        result = self.prepared()
        self.assertEqual(self.process().json(), result)
        self.assertEqual(len(self.client.get('/api/v1/extracoes_inteligentes').json()), 1)
        self.assertEqual(len(self.client.get('/api/v1/dados_extraidos').json()), 5)

    def test_confirm_human_value(self):
        field = self.prepared()['campos_encontrados'][0]
        response = self.client.patch(f"/api/v1/dados_extraidos/{field['id_dado_extraido']}/validacao", json={})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['valor_validado'], field['valor_extraido'])
        self.assertEqual(response.json()['situacao_validacao'], 'validada')

    def test_correct_human_value_preserves_original(self):
        field = self.prepared()['campos_encontrados'][0]
        response = self.client.patch(f"/api/v1/dados_extraidos/{field['id_dado_extraido']}/validacao",
                                     json={'valor_validado': '130.00'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {**field, 'valor_validado': '130.00', 'situacao_validacao': 'validada'})
        self.assertEqual(self.process().json()['campos_encontrados'][0], response.json())

    def test_validation_input(self):
        self.prepared()
        for payload in [{'valor_validado': None}, {'valor_validado': ''}, {'valor_extraido': '1'}, {'nivel_confianca': 0}]:
            self.assertEqual(self.client.patch('/api/v1/dados_extraidos/1/validacao', json=payload).status_code, 422)
        self.assertEqual(self.client.patch('/api/v1/dados_extraidos/999/validacao', json={}).status_code, 404)

    def test_invalid_pdf(self):
        self.assertEqual(self.upload(data=b'%PDF-1.4\ninvalid').status_code, 201)
        self.assertEqual(self.process().status_code, 400)
        self.assertEqual(self.client.get('/api/v1/extracoes_inteligentes').json(), [])

    def test_missing_file(self):
        doc = self.upload().json()
        (self.storage / doc['caminho_arquivo']).unlink()
        self.assertEqual(self.process().status_code, 404)

    def test_legacy_arbitrary_path_is_not_read(self):
        self.client.post('/api/v1/documentos', json={**ENTITIES[4][2], 'caminho_arquivo': '../outside.pdf'})
        self.assertEqual(self.process().status_code, 415)

    def test_no_fields_requires_manual_validation(self):
        self.upload(data=pdf('Documento sem campos identificáveis'))
        result = self.process().json()
        self.assertEqual(result['campos_encontrados'], [])
        self.assertIsNone(result['confianca_geral'])
        self.assertEqual(result['situacao'], 'requer_validacao')
        self.assertEqual(self.process().json(), result)

    def test_partial_field_failure_rolls_back_and_session_recovers(self):
        self.upload()
        with Session(self.engine) as session:
            service = ProcessamentoDocumentoService(session)
            original_create = service.fields.create
            calls = 0
            def fail_second(data):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError('falha na persistência')
                return original_create(data)
            with patch.object(service.fields, 'create', side_effect=fail_second), self.assertRaises(RuntimeError):
                service.processar(1)
            self.assertEqual(list(session.scalars(select(ExtracaoInteligente))), [])
            self.assertEqual(list(session.scalars(select(DadoExtraido))), [])
            self.assertIsNotNone(session.get(Documento, 1))
            self.assertEqual(len(service.processar(1).campos_encontrados), 5)

    def test_commit_failure_rolls_back(self):
        self.upload()
        with Session(self.engine) as session:
            service = ProcessamentoDocumentoService(session)
            with patch.object(session, 'commit', side_effect=RuntimeError('commit')), self.assertRaises(RuntimeError):
                service.processar(1)
            self.assertEqual(list(session.scalars(select(ExtracaoInteligente))), [])
            self.assertEqual(list(session.scalars(select(DadoExtraido))), [])
            self.assertEqual(len(service.processar(1).campos_encontrados), 5)

    def test_upload_failure_removes_file(self):
        with Session(self.engine) as session:
            service = ProcessamentoDocumentoService(session)
            with patch.object(session, 'commit', side_effect=RuntimeError('commit')), self.assertRaises(RuntimeError):
                service.upload(1, BytesIO(pdf(TEXT)), 'test.pdf', 'application/pdf')
            self.assertEqual(list(self.storage.glob('*.pdf')), [])
            self.assertEqual(list(session.scalars(select(Documento))), [])
            self.assertEqual(service.upload(1, BytesIO(pdf(TEXT)), 'test.pdf', 'application/pdf').id_conta, 1)

    def test_sql_flush_failure_rolls_back_and_session_recovers(self):
        self.upload()
        with Session(self.engine) as session:
            service = ProcessamentoDocumentoService(session)
            original_create = service.fields.create
            calls = 0

            def fail_second(data):
                nonlocal calls
                calls += 1
                instance = original_create(data)
                if calls == 2:
                    instance.campo_identificado = None
                    session.flush()  # Falha real de NOT NULL, sessão entra em estado de erro.
                return instance

            with patch.object(service.fields, 'create', side_effect=fail_second), self.assertRaises(IntegrityError):
                service.processar(1)
            self.assertEqual(list(session.scalars(select(ExtracaoInteligente))), [])
            self.assertEqual(list(session.scalars(select(DadoExtraido))), [])
            self.assertEqual(len(service.processar(1).campos_encontrados), 5)

    def test_upload_and_processing_without_network(self):
        with patch('socket.socket.connect', side_effect=AssertionError('acesso à rede proibido')):
            result = self.prepared()
        self.assertEqual(len(result['campos_encontrados']), 5)

    def test_validation_commit_failure_preserves_values(self):
        field = self.prepared()['campos_encontrados'][0]
        from app.services.dado_extraido import DadoExtraidoService
        from app.schemas.dado_extraido import DadoExtraidoValidacao
        with Session(self.engine) as session:
            service = DadoExtraidoService(session)
            with patch.object(session, 'commit', side_effect=RuntimeError('commit')), self.assertRaises(RuntimeError):
                service.validar(field['id_dado_extraido'], DadoExtraidoValidacao(valor_validado='130.00'))
            instance = service.get_by_id(field['id_dado_extraido'])
            self.assertIsNone(instance.valor_validado)
            self.assertEqual(instance.valor_extraido, field['valor_extraido'])
            self.assertEqual(instance.situacao_validacao, 'pendente')
            self.assertEqual(service.validar(instance.id_dado_extraido, DadoExtraidoValidacao()).situacao_validacao, 'validada')


class ExtractorTests(unittest.TestCase):
    def test_text_and_page_count(self):
        result = PdfTextExtractor().extract(pdf(TEXT))
        self.assertTrue(result.sucesso)
        self.assertEqual(result.quantidade_paginas, 1)
        self.assertIn('123,45', result.texto)

    def test_ambiguous_fields_are_omitted(self):
        for text in ['Valor total: 10,00\nValor total: 20,00',
                     'Valor total: 10,00\nTotal a pagar: ilegível', 'Vencimento: 31/02/2026',
                     'Valor total: 10,00 ou 20,00', 'Competência: 13/2026',
                     'Consumo: 123', 'Código de barras: 1234']:
            with self.subTest(text=text):
                self.assertEqual(DeterministicFieldExtractor().extract(text), [])

    def test_duplicate_identical_values_are_safe(self):
        fields = DeterministicFieldExtractor().extract('Valor total: 10,00\nTotal a pagar: R$ 10,00')
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].valor_extraido, '10.00')
