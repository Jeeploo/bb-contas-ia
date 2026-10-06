from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.processamento_documento import ProcessamentoDocumentoRead
from app.services.processamento_documento import ProcessamentoDocumentoService
from app.schemas.documento import DocumentoCreate, DocumentoRead, DocumentoUpdate
from app.services.documento import DocumentoService


router = APIRouter(
    prefix="/documentos", tags=["Documento"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=DocumentoRead, status_code=status.HTTP_201_CREATED)
def create(data: DocumentoCreate, session: DatabaseSession):
    return DocumentoService(session).create(data)


@router.get("", response_model=list[DocumentoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return DocumentoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=DocumentoRead)
def get_by_id(id: int, session: DatabaseSession):
    return DocumentoService(session).get_by_id(id)


@router.patch("/{id}", response_model=DocumentoRead)
def update(id: int, data: DocumentoUpdate, session: DatabaseSession):
    return DocumentoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    DocumentoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id_documento}/processar", response_model=ProcessamentoDocumentoRead)
def processar(id_documento: int, session: DatabaseSession):
    return ProcessamentoDocumentoService(session).processar(id_documento)
