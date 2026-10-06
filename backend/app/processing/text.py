from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

from pypdf import PdfReader

from app.services.exceptions import InvalidPdfError, PdfWithoutTextError


@dataclass(frozen=True)
class TextExtractionResult:
    texto: str
    quantidade_paginas: int
    sucesso: bool


class DocumentTextExtractor(Protocol):
    def extract(self, content: bytes) -> TextExtractionResult: ...


class PdfTextExtractor:
    def extract(self, content: bytes) -> TextExtractionResult:
        try:
            if not content.startswith(b"%PDF-"):
                raise ValueError("Assinatura PDF inválida")
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ValueError("PDF protegido por senha")
            pages = len(reader.pages)
            if not pages:
                raise ValueError("PDF sem páginas")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise InvalidPdfError("PDF inválido ou protegido; leitura indisponível") from exc
        if not text.strip():
            raise PdfWithoutTextError("PDF sem camada textual; OCR ou tratamento manual necessário")
        return TextExtractionResult(text, pages, True)
