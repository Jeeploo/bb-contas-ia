from decimal import Decimal
from pydantic import BaseModel

from app.schemas.documento import DocumentoRead
from app.schemas.extracao_inteligente import ExtracaoInteligenteRead
from app.schemas.dado_extraido import DadoExtraidoRead


class ProcessamentoDocumentoRead(BaseModel):
    documento: DocumentoRead
    extracao: ExtracaoInteligenteRead
    campos_encontrados: list[DadoExtraidoRead]
    confianca_geral: Decimal | None
    situacao: str
