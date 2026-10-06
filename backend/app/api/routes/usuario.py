from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.services.usuario import UsuarioService


router = APIRouter(
    prefix="/usuarios", tags=["Usuario"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def create(data: UsuarioCreate, session: DatabaseSession):
    return UsuarioService(session).create(data)


@router.get("", response_model=list[UsuarioRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return UsuarioService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=UsuarioRead)
def get_by_id(id: int, session: DatabaseSession):
    return UsuarioService(session).get_by_id(id)


@router.patch("/{id}", response_model=UsuarioRead)
def update(id: int, data: UsuarioUpdate, session: DatabaseSession):
    return UsuarioService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    UsuarioService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
