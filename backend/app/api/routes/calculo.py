from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.calculo import CalculoCreate, CalculoRead, CalculoUpdate
from app.services.calculo import CalculoService


router = APIRouter(
    prefix="/calculos", tags=["Calculo"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=CalculoRead, status_code=status.HTTP_201_CREATED)
def create(data: CalculoCreate, session: DatabaseSession):
    return CalculoService(session).create(data)


@router.get("", response_model=list[CalculoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return CalculoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=CalculoRead)
def get_by_id(id: int, session: DatabaseSession):
    return CalculoService(session).get_by_id(id)


@router.patch("/{id}", response_model=CalculoRead)
def update(id: int, data: CalculoUpdate, session: DatabaseSession):
    return CalculoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    CalculoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
