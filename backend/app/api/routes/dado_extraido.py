from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.dado_extraido import DadoExtraidoValidacao
from app.schemas.dado_extraido import DadoExtraidoCreate, DadoExtraidoRead, DadoExtraidoUpdate
from app.services.dado_extraido import DadoExtraidoService


router = APIRouter(
    prefix="/dados_extraidos", tags=["DadoExtraido"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=DadoExtraidoRead, status_code=status.HTTP_201_CREATED)
def create(data: DadoExtraidoCreate, session: DatabaseSession):
    return DadoExtraidoService(session).create(data)


@router.get("", response_model=list[DadoExtraidoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return DadoExtraidoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=DadoExtraidoRead)
def get_by_id(id: int, session: DatabaseSession):
    return DadoExtraidoService(session).get_by_id(id)


@router.patch("/{id}", response_model=DadoExtraidoRead)
def update(id: int, data: DadoExtraidoUpdate, session: DatabaseSession):
    return DadoExtraidoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    DadoExtraidoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{id}/validacao", response_model=DadoExtraidoRead)
def validar(id: int, data: DadoExtraidoValidacao, session: DatabaseSession):
    return DadoExtraidoService(session).validar(id, data)
