from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.perfil_processamento import PerfilProcessamentoCreate, PerfilProcessamentoRead, PerfilProcessamentoUpdate
from app.services.perfil_processamento import PerfilProcessamentoService


router = APIRouter(
    prefix="/perfis_processamento", tags=["PerfilProcessamento"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=PerfilProcessamentoRead, status_code=status.HTTP_201_CREATED)
def create(data: PerfilProcessamentoCreate, session: DatabaseSession):
    return PerfilProcessamentoService(session).create(data)


@router.get("", response_model=list[PerfilProcessamentoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return PerfilProcessamentoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=PerfilProcessamentoRead)
def get_by_id(id: int, session: DatabaseSession):
    return PerfilProcessamentoService(session).get_by_id(id)


@router.patch("/{id}", response_model=PerfilProcessamentoRead)
def update(id: int, data: PerfilProcessamentoUpdate, session: DatabaseSession):
    return PerfilProcessamentoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    PerfilProcessamentoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
