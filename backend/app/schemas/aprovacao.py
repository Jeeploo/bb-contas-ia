from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AprovacaoBase(BaseModel):
    data_hora: datetime
    decisao: str
    observacao: str | None = None
    id_ordem: int
    id_usuario: int


class AprovacaoCreate(AprovacaoBase):
    id_usuario: int | None = None
    model_config = ConfigDict(extra="forbid")


class AprovacaoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_hora: datetime | None = None
    decisao: str | None = None
    observacao: str | None = None
    id_ordem: int | None = None
    id_usuario: int | None = None


class AprovacaoRead(AprovacaoBase):
    model_config = ConfigDict(from_attributes=True)

    id_aprovacao: int
