from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.item_pagamento import ItemPagamentoCreate, ItemPagamentoRead, ItemPagamentoUpdate
from app.services.item_pagamento import ItemPagamentoService


router = APIRouter(
    prefix="/itens_pagamento", tags=["ItemPagamento"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ItemPagamentoRead, status_code=status.HTTP_201_CREATED)
def create(data: ItemPagamentoCreate, session: DatabaseSession):
    return ItemPagamentoService(session).create(data)


@router.get("", response_model=list[ItemPagamentoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return ItemPagamentoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=ItemPagamentoRead)
def get_by_id(id: int, session: DatabaseSession):
    return ItemPagamentoService(session).get_by_id(id)


@router.patch("/{id}", response_model=ItemPagamentoRead)
def update(id: int, data: ItemPagamentoUpdate, session: DatabaseSession):
    return ItemPagamentoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    ItemPagamentoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
