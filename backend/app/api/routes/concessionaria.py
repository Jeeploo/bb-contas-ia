from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.concessionaria import ConcessionariaCreate, ConcessionariaRead, ConcessionariaUpdate
from app.services.concessionaria import ConcessionariaService


router = APIRouter(
    prefix="/concessionarias", tags=["Concessionaria"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ConcessionariaRead, status_code=status.HTTP_201_CREATED)
def create(data: ConcessionariaCreate, session: DatabaseSession):
    return ConcessionariaService(session).create(data)


@router.get("", response_model=list[ConcessionariaRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return ConcessionariaService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=ConcessionariaRead)
def get_by_id(id: int, session: DatabaseSession):
    return ConcessionariaService(session).get_by_id(id)


@router.patch("/{id}", response_model=ConcessionariaRead)
def update(id: int, data: ConcessionariaUpdate, session: DatabaseSession):
    return ConcessionariaService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    ConcessionariaService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
