from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.item_extraido import ItemExtraidoRead, ItemExtraidoValidacao
from app.services.item_extraido import ItemExtraidoService

router = APIRouter(prefix="/itens_extraidos", tags=["ItemExtraido"], route_class=EntityNotFoundRoute)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ItemExtraidoRead])
def list_entities(session: DatabaseSession, offset: Annotated[int, Query(ge=0)] = 0,
                  limit: Annotated[int, Query(gt=0)] = 100):
    return ItemExtraidoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=ItemExtraidoRead)
def get_by_id(id: int, session: DatabaseSession):
    return ItemExtraidoService(session).get_by_id(id)


@router.patch("/{id}/validacao", response_model=ItemExtraidoRead)
def validar(id: int, data: ItemExtraidoValidacao, session: DatabaseSession):
    return ItemExtraidoService(session).validar(id, data)
