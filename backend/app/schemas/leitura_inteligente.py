from pydantic import BaseModel
from app.schemas.dado_extraido import DadoExtraidoRead
from app.schemas.processamento_documento import ProcessamentoDocumentoRead


class DadoLeituraRead(DadoExtraidoRead):
    valor_normalizado: str | None = None


class ProcessamentoInteligenteRead(ProcessamentoDocumentoRead):
    campos_encontrados: list[DadoLeituraRead]
    metadados_ia: dict


class TentativasLeituraRead(BaseModel):
    tentativas: list[dict]
