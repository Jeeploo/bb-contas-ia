from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.api.auth_dependencies import get_current_user
from app.schemas.ordem_pagamento import OrdemPagamentoCreate, OrdemPagamentoRead, OrdemPagamentoUpdate
from app.services.ordem_pagamento import OrdemPagamentoService


router = APIRouter(
    prefix="/ordens_pagamento", tags=["OrdemPagamento"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=OrdemPagamentoRead, status_code=status.HTTP_201_CREATED)
def create(data: OrdemPagamentoCreate, session: DatabaseSession, user=Depends(get_current_user)):
    if user is not None:  # Production dependency always returns an authenticated user.
        data = data.model_copy(update={"id_usuario_criador": user.id_usuario})
    return OrdemPagamentoService(session).create(data)


@router.get("", response_model=list[OrdemPagamentoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return OrdemPagamentoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=OrdemPagamentoRead)
def get_by_id(id: int, session: DatabaseSession):
    return OrdemPagamentoService(session).get_by_id(id)


@router.patch("/{id}", response_model=OrdemPagamentoRead)
def update(id: int, data: OrdemPagamentoUpdate, session: DatabaseSession):
    return OrdemPagamentoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    OrdemPagamentoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
