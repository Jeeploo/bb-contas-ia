from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.prefixo import PrefixoCreate, PrefixoRead, PrefixoUpdate
from app.services.prefixo import PrefixoService


router = APIRouter(
    prefix="/prefixos", tags=["Prefixo"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=PrefixoRead, status_code=status.HTTP_201_CREATED)
def create(data: PrefixoCreate, session: DatabaseSession):
    return PrefixoService(session).create(data)


@router.get("", response_model=list[PrefixoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return PrefixoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=PrefixoRead)
def get_by_id(id: int, session: DatabaseSession):
    return PrefixoService(session).get_by_id(id)


@router.patch("/{id}", response_model=PrefixoRead)
def update(id: int, data: PrefixoUpdate, session: DatabaseSession):
    return PrefixoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    PrefixoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
