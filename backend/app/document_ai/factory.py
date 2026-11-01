"""Seleção centralizada, sem fallback ou chamadas externas na construção."""
from app.core.config import settings
from app.document_ai.base import DocumentAIError, DocumentAIProvider
from app.document_ai.openai_provider import OpenAIDocumentAIProvider


def get_document_ai_provider() -> DocumentAIProvider:
    name = settings.document_ai_provider
    if name == 'openai':
        return OpenAIDocumentAIProvider()
    if name == 'gemini':
        from app.document_ai.gemini_provider import GeminiDocumentAIProvider
        return GeminiDocumentAIProvider()
    raise DocumentAIError('document_ai_provider_desconhecido', 503)
