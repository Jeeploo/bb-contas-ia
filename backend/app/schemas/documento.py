from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentoBase(BaseModel):
    tipo_documento: str
    formato: str
    data_recebimento: datetime
    origem: str
    caminho_arquivo: str
    id_conta: int | None = None


class DocumentoCreate(DocumentoBase):
    model_config = ConfigDict(extra="forbid")


class DocumentoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_documento: str | None = None
    formato: str | None = None
    data_recebimento: datetime | None = None
    origem: str | None = None
    caminho_arquivo: str | None = None
    id_conta: int | None = None


class DocumentoRead(DocumentoBase):
    model_config = ConfigDict(from_attributes=True)

    id_documento: int
