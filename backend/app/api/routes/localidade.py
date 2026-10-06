from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.localidade import LocalidadeCreate, LocalidadeRead, LocalidadeUpdate
from app.services.localidade import LocalidadeService


router = APIRouter(
    prefix="/localidades", tags=["Localidade"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=LocalidadeRead, status_code=status.HTTP_201_CREATED)
def create(data: LocalidadeCreate, session: DatabaseSession):
    return LocalidadeService(session).create(data)


@router.get("", response_model=list[LocalidadeRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return LocalidadeService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=LocalidadeRead)
def get_by_id(id: int, session: DatabaseSession):
    return LocalidadeService(session).get_by_id(id)


@router.patch("/{id}", response_model=LocalidadeRead)
def update(id: int, data: LocalidadeUpdate, session: DatabaseSession):
    return LocalidadeService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    LocalidadeService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
