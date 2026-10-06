from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.documento import DocumentoRead
from app.services.processamento_documento import ProcessamentoDocumentoService
from app.schemas.conta_consumo import ContaConsumoCreate, ContaConsumoRead, ContaConsumoUpdate
from app.services.conta_consumo import ContaConsumoService


router = APIRouter(
    prefix="/contas_consumo", tags=["ContaConsumo"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ContaConsumoRead, status_code=status.HTTP_201_CREATED)
def create(data: ContaConsumoCreate, session: DatabaseSession):
    return ContaConsumoService(session).create(data)


@router.get("", response_model=list[ContaConsumoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return ContaConsumoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=ContaConsumoRead)
def get_by_id(id: int, session: DatabaseSession):
    return ContaConsumoService(session).get_by_id(id)


@router.patch("/{id}", response_model=ContaConsumoRead)
def update(id: int, data: ContaConsumoUpdate, session: DatabaseSession):
    return ContaConsumoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    ContaConsumoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id_conta}/documentos/upload", response_model=DocumentoRead,
             status_code=status.HTTP_201_CREATED)
def upload_documento(id_conta: int, session: DatabaseSession, file: UploadFile):
    return ProcessamentoDocumentoService(session).upload(
        id_conta, file.file, file.filename or "", file.content_type or "")
