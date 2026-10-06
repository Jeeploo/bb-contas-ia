from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.extracao_inteligente import ExtracaoInteligenteCreate, ExtracaoInteligenteRead, ExtracaoInteligenteUpdate
from app.services.extracao_inteligente import ExtracaoInteligenteService


router = APIRouter(
    prefix="/extracoes_inteligentes", tags=["ExtracaoInteligente"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ExtracaoInteligenteRead, status_code=status.HTTP_201_CREATED)
def create(data: ExtracaoInteligenteCreate, session: DatabaseSession):
    return ExtracaoInteligenteService(session).create(data)


@router.get("", response_model=list[ExtracaoInteligenteRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return ExtracaoInteligenteService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=ExtracaoInteligenteRead)
def get_by_id(id: int, session: DatabaseSession):
    return ExtracaoInteligenteService(session).get_by_id(id)


@router.patch("/{id}", response_model=ExtracaoInteligenteRead)
def update(id: int, data: ExtracaoInteligenteUpdate, session: DatabaseSession):
    return ExtracaoInteligenteService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    ExtracaoInteligenteService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
