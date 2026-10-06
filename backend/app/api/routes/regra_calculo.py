from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.regra_calculo import RegraCalculoCreate, RegraCalculoRead, RegraCalculoUpdate
from app.services.regra_calculo import RegraCalculoService


router = APIRouter(
    prefix="/regras_calculo", tags=["RegraCalculo"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=RegraCalculoRead, status_code=status.HTTP_201_CREATED)
def create(data: RegraCalculoCreate, session: DatabaseSession):
    return RegraCalculoService(session).create(data)


@router.get("", response_model=list[RegraCalculoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return RegraCalculoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=RegraCalculoRead)
def get_by_id(id: int, session: DatabaseSession):
    return RegraCalculoService(session).get_by_id(id)


@router.patch("/{id}", response_model=RegraCalculoRead)
def update(id: int, data: RegraCalculoUpdate, session: DatabaseSession):
    return RegraCalculoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    RegraCalculoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
