from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from app.services.exceptions import (
    DocumentFileNotFoundError, DocumentTooLargeError, EmptyDocumentError,
    InvalidPdfError, UnsupportedDocumentFormatError,
)


class DocumentStorage(Protocol):
    def save(self, source: BinaryIO, filename: str, content_type: str) -> str: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class LocalDocumentStorage:
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
