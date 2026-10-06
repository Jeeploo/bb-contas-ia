from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.item_regra import ItemRegraCreate, ItemRegraRead, ItemRegraUpdate
from app.services.item_regra import ItemRegraService


router = APIRouter(
    prefix="/itens_regra", tags=["ItemRegra"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ItemRegraRead, status_code=status.HTTP_201_CREATED)
def create(data: ItemRegraCreate, session: DatabaseSession):
    return ItemRegraService(session).create(data)


@router.get("", response_model=list[ItemRegraRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return ItemRegraService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=ItemRegraRead)
def get_by_id(id: int, session: DatabaseSession):
    return ItemRegraService(session).get_by_id(id)


@router.patch("/{id}", response_model=ItemRegraRead)
def update(id: int, data: ItemRegraUpdate, session: DatabaseSession):
    return ItemRegraService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    ItemRegraService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
