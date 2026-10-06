from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.alcada import AlcadaCreate, AlcadaRead, AlcadaUpdate
from app.services.alcada import AlcadaService


router = APIRouter(
    prefix="/alcadas", tags=["Alcada"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=AlcadaRead, status_code=status.HTTP_201_CREATED)
def create(data: AlcadaCreate, session: DatabaseSession):
    return AlcadaService(session).create(data)


@router.get("", response_model=list[AlcadaRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return AlcadaService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=AlcadaRead)
def get_by_id(id: int, session: DatabaseSession):
    return AlcadaService(session).get_by_id(id)


@router.patch("/{id}", response_model=AlcadaRead)
def update(id: int, data: AlcadaUpdate, session: DatabaseSession):
    return AlcadaService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    AlcadaService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
