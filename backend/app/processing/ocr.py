"""Fallback local: pypdf primeiro, renderização e Tesseract apenas sem texto."""
import pymupdf
import pytesseract
from PIL import Image

from app.processing.text import DocumentTextExtractor, PdfTextExtractor, TextExtractionResult
from app.services.exceptions import (
    PdfWithoutTextError, TesseractUnavailableError, OcrLanguageUnavailableError,
    OcrPageLimitExceededError, PdfRenderingError, EmptyOcrError, OcrExecutionError,
)


class TesseractPdfOcrExtractor:
    def __init__(self, max_pages: int = 10):
        if max_pages < 1:
            raise ValueError("MAX_OCR_PAGES deve ser positivo")
        self.max_pages = max_pages

    def extract(self, content: bytes) -> TextExtractionResult:
        try:
            document = pymupdf.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise PdfRenderingError("Falha ao abrir PDF para renderização") from exc
        with document:
            pages = len(document)
            if pages > self.max_pages:
                raise OcrPageLimitExceededError(f"OCR limitado a {self.max_pages} páginas")
            try:
                languages = pytesseract.get_languages(config="")
            except (pytesseract.TesseractNotFoundError, FileNotFoundError) as exc:
                raise TesseractUnavailableError("Tesseract indisponível") from exc
            except pytesseract.TesseractError as exc:
                raise OcrExecutionError("Falha ao consultar idiomas OCR") from exc
            language = next((lang for lang in ("por", "eng") if lang in languages), None)
            if language is None:
                raise OcrLanguageUnavailableError("OCR requer idioma por ou eng instalado")
            texts = []
            for page in document:
                try:
                    pixmap = page.get_pixmap(dpi=300, colorspace=pymupdf.csRGB, alpha=False)
                    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                except Exception as exc:
                    raise PdfRenderingError("Falha na renderização de página PDF") from exc
                try:
                    with image:
                        texts.append(pytesseract.image_to_string(image, lang=language, timeout=60))
                except (pytesseract.TesseractNotFoundError, FileNotFoundError) as exc:
                    raise TesseractUnavailableError("Tesseract indisponível") from exc
                except (pytesseract.TesseractError, RuntimeError) as exc:
                    raise OcrExecutionError("Falha na execução do OCR") from exc
            text = "\n".join(texts)
            if not any(char.isalnum() for char in text):
                raise EmptyOcrError("OCR sem texto utilizável; tratamento manual necessário")
            return TextExtractionResult(text, pages, True, "ocr", 80)


class HybridPdfTextExtractor:
    def __init__(self, native: DocumentTextExtractor | None = None,
                 ocr: DocumentTextExtractor | None = None, max_pages: int = 10):
        self.native = native or PdfTextExtractor()
        self.ocr = ocr or TesseractPdfOcrExtractor(max_pages)

    def extract(self, content: bytes) -> TextExtractionResult:
        try:
            result = self.native.extract(content)
        except PdfWithoutTextError:
            return self.ocr.extract(content)
        if not result.texto.strip():
            return self.ocr.extract(content)
        return result
