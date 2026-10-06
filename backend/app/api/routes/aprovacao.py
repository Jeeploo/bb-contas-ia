from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db
from app.schemas.aprovacao import AprovacaoCreate, AprovacaoRead, AprovacaoUpdate
from app.services.aprovacao import AprovacaoService


router = APIRouter(
    prefix="/aprovacoes", tags=["Aprovacao"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=AprovacaoRead, status_code=status.HTTP_201_CREATED)
def create(data: AprovacaoCreate, session: DatabaseSession):
    return AprovacaoService(session).create(data)


@router.get("", response_model=list[AprovacaoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return AprovacaoService(session).list(offset=offset, limit=limit)


@router.get("/{id}", response_model=AprovacaoRead)
def get_by_id(id: int, session: DatabaseSession):
    return AprovacaoService(session).get_by_id(id)


@router.patch("/{id}", response_model=AprovacaoRead)
def update(id: int, data: AprovacaoUpdate, session: DatabaseSession):
    return AprovacaoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    AprovacaoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
