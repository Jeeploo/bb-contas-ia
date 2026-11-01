from dataclasses import dataclass
from typing import Protocol
from app.schemas.leitura_documental import LeituraDocumental


@dataclass(frozen=True)
class InterpretacaoAI:
    leitura: LeituraDocumental
    original: dict
    metadados: dict


class DocumentAIProvider(Protocol):
    provider: str
    modelo: str

    def interpretar_documento(self, data: bytes, mime_type: str) -> InterpretacaoAI: ...


class DocumentAIError(Exception):
    """Somente código seguro; nunca propagar corpo/headers/URL do fornecedor."""
    def __init__(self, codigo: str, http_status: int = 502, metadados: dict | None = None):
        self.codigo = codigo
        self.http_status = http_status
        self.metadados = metadados or {}
        super().__init__(codigo)
