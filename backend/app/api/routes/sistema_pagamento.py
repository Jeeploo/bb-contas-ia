from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.sistema_pagamento import SistemaPagamentoCreate, SistemaPagamentoRead, SistemaPagamentoUpdate
from app.services.sistema_pagamento import SistemaPagamentoService


router = APIRouter(
    prefix="/sistemas_pagamento", tags=["SistemaPagamento"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=SistemaPagamentoRead, status_code=status.HTTP_201_CREATED)
def create(data: SistemaPagamentoCreate, session: DatabaseSession):
    return SistemaPagamentoService(session).create(data)


@router.get("", response_model=list[SistemaPagamentoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return SistemaPagamentoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=SistemaPagamentoRead)
def get_by_id(id: int, session: DatabaseSession):
    return SistemaPagamentoService(session).get_by_id(id)


@router.patch("/{id}", response_model=SistemaPagamentoRead)
def update(id: int, data: SistemaPagamentoUpdate, session: DatabaseSession):
    return SistemaPagamentoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    SistemaPagamentoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
