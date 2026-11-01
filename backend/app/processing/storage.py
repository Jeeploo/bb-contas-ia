from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from app.services.exceptions import (
    DocumentFileNotFoundError, DocumentTooLargeError, EmptyDocumentError,
    InvalidPdfError, UnsupportedDocumentFormatError,
)


class DocumentStorage(Protocol):
    provider: str
    def save(self, source: BinaryIO, filename: str, content_type: str) -> str: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class LocalDocumentStorage:
    provider = "local"
    def __init__(self, directory: str, max_size: int = 10 * 1024 * 1024):
        self.directory = Path(directory).resolve()
        self.max_size = max_size

    def _path(self, key: str) -> Path:
        path = (self.directory / key).resolve()
        if path.parent != self.directory:
            raise UnsupportedDocumentFormatError("Caminho fora do armazenamento de documentos")
        return path

    def save(self, source: BinaryIO, filename: str, content_type: str) -> str:
        from app.processing.arquivo_documental import mime_arquivo, validar_arquivo
        mime = mime_arquivo(filename, content_type)
        # Leitura limitada antes de criar qualquer diretório ou arquivo.
        data = source.read(self.max_size + 1)
        if len(data) > self.max_size:
            raise DocumentTooLargeError("Documento excede o limite de tamanho")
        if not data:
            raise EmptyDocumentError("Arquivo vazio")
        validar_arquivo(data, mime)
        key = f"{uuid4().hex}{Path(filename).suffix.lower()}"
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        try:
            with path.open("xb") as target:
                target.write(data)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return key

    def read(self, key: str) -> bytes:
        path = self._path(key)
        try:
            with path.open("rb") as source:
                data = source.read(self.max_size + 1)
        except FileNotFoundError as exc:
            raise DocumentFileNotFoundError("Arquivo do documento não encontrado") from exc
        if len(data) > self.max_size:
            raise DocumentTooLargeError("Documento excede o limite de tamanho")
        return data

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


def get_document_storage(provider=None):
    """Seleciona pelo registro do documento; configuração é só default de upload."""
    from app.core.config import settings
    from app.services.exceptions import DocumentStorageError
    provider = provider or settings.document_storage_provider
    if provider == 'local':
        return LocalDocumentStorage(settings.document_storage_path, settings.document_max_size_bytes)
    if provider == 'r2':
        try:
            settings.validate_r2()
        except ValueError:
            raise DocumentStorageError('Configuração do storage externo indisponível') from None
        from app.processing.r2_storage import R2DocumentStorage
        return R2DocumentStorage(bucket=settings.r2_bucket, endpoint=settings.r2_endpoint,
            access_key_id=settings.r2_access_key_id, secret_access_key=settings.r2_secret_access_key,
            region=settings.r2_region, max_size=settings.document_max_size_bytes)
    raise DocumentStorageError('Provider de storage não suportado')


def storage_for_document(document, override=None):
    return override if override is not None else get_document_storage(document.storage_provider or 'local')


def document_storage_key(document):
    # Referências legadas não são tratadas como pertencentes ao provider global atual.
    return document.storage_key if document.storage_key is not None else document.caminho_arquivo
