from io import BytesIO
from unittest.mock import Mock, patch
import unittest
import pymupdf
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import DadoExtraido, ExtracaoInteligente
from app.processing.ocr import HybridPdfTextExtractor, TesseractPdfOcrExtractor
from app.processing.fields import DeterministicFieldExtractor
from app.services.exceptions import (InvalidPdfError, EmptyOcrError, TesseractUnavailableError, OcrLanguageUnavailableError, OcrPageLimitExceededError, PdfRenderingError)
from app.services.processamento_documento import ProcessamentoDocumentoService
from tests import test_processamento_documento as flow
from tests.test_api import ApiTestCase


def image_pdf():
    image = Image.new('RGB', (1400, 400), 'white')
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 45)
    ImageDraw.Draw(image).text((60, 70), 'Valor total: R$ 123,45\nVencimento: 20/10/2026', font=font, fill='black')
    output = BytesIO()
    image.save(output, format='PNG')
    with pymupdf.open() as document:
        document.new_page(width=700, height=200).insert_image(pymupdf.Rect(0, 0, 700, 200), stream=output.getvalue())
        return document.tobytes()


class OcrTests(unittest.TestCase):
    def test_text_uses_pypdf_never_tesseract(self):
        import app.processing.text as module
        with patch.object(module, 'PdfReader', wraps=module.PdfReader) as reader, patch('pytesseract.get_languages') as langs, patch('pytesseract.image_to_string') as ocr:
            result = HybridPdfTextExtractor().extract(flow.pdf(flow.TEXT))
        reader.assert_called_once()
        langs.assert_not_called()
        ocr.assert_not_called()
        self.assertEqual(result.estrategia, 'text')
        self.assertEqual(result.confianca_base, 95)

    def test_image_ocr_text_and_language_fallback(self):
        for languages, expected in [(['por', 'eng'], 'por'), (['eng'], 'eng')]:
            with patch('pytesseract.get_languages', return_value=languages), patch('pytesseract.image_to_string', return_value=flow.TEXT) as ocr:
                result = HybridPdfTextExtractor().extract(image_pdf())
            self.assertEqual(result.texto, flow.TEXT)
            self.assertEqual(result.estrategia, 'ocr')
            self.assertEqual(result.confianca_base, 80)
            self.assertEqual(ocr.call_args.kwargs['lang'], expected)

    def test_ocr_page_by_page(self):
        with pymupdf.open() as document:
            document.new_page()
            document.new_page()
            content = document.tobytes()
        with patch('pytesseract.get_languages', return_value=['por']), patch('pytesseract.image_to_string', side_effect=['primeira', 'segunda']) as ocr:
            result = HybridPdfTextExtractor().extract(content)
        self.assertEqual(ocr.call_count, 2)
        self.assertEqual(result.quantidade_paginas, 2)
        self.assertEqual(result.texto, 'primeira\nsegunda')

    def test_page_limit(self):
        with pymupdf.open() as document:
            for _ in range(11):
                document.new_page()
            content = document.tobytes()
        with patch('pytesseract.get_languages') as langs, self.assertRaises(OcrPageLimitExceededError):
            HybridPdfTextExtractor().extract(content)
        langs.assert_not_called()

    def test_unavailable_tesseract(self):
        with patch('pytesseract.get_languages', side_effect=pytesseract.TesseractNotFoundError()), self.assertRaises(TesseractUnavailableError):
            HybridPdfTextExtractor().extract(flow.pdf())

    def test_unavailable_language(self):
        with patch('pytesseract.get_languages', return_value=['osd']), self.assertRaises(OcrLanguageUnavailableError):
            HybridPdfTextExtractor().extract(flow.pdf())

    def test_empty_ocr(self):
        for text in ['', ' \n', '...']:
            with patch('pytesseract.get_languages', return_value=['por']), patch('pytesseract.image_to_string', return_value=text), self.assertRaises(EmptyOcrError):
                HybridPdfTextExtractor().extract(flow.pdf())

    def test_invalid_pdf(self):
        ocr = Mock()
        with self.assertRaises(InvalidPdfError):
            HybridPdfTextExtractor(ocr=ocr).extract(b'%PDF-invalid')
        ocr.extract.assert_not_called()

    def test_rendering_failure(self):
        with patch('pymupdf.Page.get_pixmap', side_effect=RuntimeError('render')), patch('pytesseract.get_languages', return_value=['por']), self.assertRaises(PdfRenderingError):
            HybridPdfTextExtractor().extract(flow.pdf())

    def test_real_tesseract_without_internet(self):
        with patch('socket.socket.connect', side_effect=AssertionError('rede proibida')):
            result = HybridPdfTextExtractor().extract(image_pdf())
        self.assertEqual(result.estrategia, 'ocr')
        self.assertIn('123,45', result.texto)
        self.assertEqual(DeterministicFieldExtractor().extract(result.texto)[0].valor_extraido, '123.45')


class OcrFlowTests(ApiTestCase):
    def setUp(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from app.core.config import settings
        from tests.test_api import ENTITIES
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

    upload = flow.DocumentFlowTests.upload
    process = flow.DocumentFlowTests.process

    def test_ocr_fields_persistence_confidence(self):
        self.upload(data=image_pdf())
        fields = Mock(wraps=DeterministicFieldExtractor())
        with Session(self.engine) as session, patch('pytesseract.get_languages', return_value=['por']), patch('pytesseract.image_to_string', return_value=flow.TEXT):
            result = ProcessamentoDocumentoService(session, field_extractor=fields).processar(1)
            fields.extract.assert_called_once_with(flow.TEXT)
            self.assertEqual(len(list(session.scalars(select(DadoExtraido)))), 5)
            self.assertEqual(result.confianca_geral, 80)
            self.assertLess(result.confianca_geral, 95)
            self.assertTrue(all(f.nivel_confianca == 80 for f in result.campos_encontrados))
        response = self.process()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('texto', response.json())

    def test_ocr_sql_rollback_session_recovery(self):
        from sqlalchemy.exc import IntegrityError
        self.upload(data=image_pdf())
        with Session(self.engine) as session, patch('pytesseract.get_languages', return_value=['por']), patch('pytesseract.image_to_string', return_value=flow.TEXT):
            service = ProcessamentoDocumentoService(session)
            original = service.fields.create
            def fail(data):
                instance = original(data)
                instance.campo_identificado = None
                session.flush()
            with patch.object(service.fields, 'create', side_effect=fail), self.assertRaises(IntegrityError):
                service.processar(1)
            self.assertEqual(list(session.scalars(select(DadoExtraido))), [])
            self.assertEqual(list(session.scalars(select(ExtracaoInteligente))), [])
            self.assertEqual(len(service.processar(1).campos_encontrados), 5)

    def test_domain_errors_http_and_rollback(self):
        self.upload(data=image_pdf())
        for error, code in [(TesseractUnavailableError('ausente'), 503), (OcrLanguageUnavailableError('idioma'), 503), (OcrPageLimitExceededError('limite'), 413), (PdfRenderingError('render'), 422), (EmptyOcrError('vazio'), 422)]:
            with patch.object(TesseractPdfOcrExtractor, 'extract', side_effect=error):
                self.assertEqual(self.process().status_code, code)
            self.assertEqual(self.client.get('/api/v1/extracoes_inteligentes').json(), [])
