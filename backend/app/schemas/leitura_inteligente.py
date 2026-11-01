from pydantic import BaseModel
from app.schemas.processamento_documento import ProcessamentoDocumentoRead


class ProcessamentoInteligenteRead(ProcessamentoDocumentoRead):
    metadados_ia: dict


class TentativasLeituraRead(BaseModel):
    tentativas: list[dict]
