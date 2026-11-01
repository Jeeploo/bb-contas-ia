from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)


class BaseRepository(Generic[ModelT, CreateT, UpdateT]):
    """CRUD compartilhado; o chamador controla commit e rollback.

    Erros de persistência são propagados para o chamador. Atualizações
    preservam campos omitidos e aplicam valores None explicitamente enviados.
    """

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: CreateT) -> ModelT:
        instance = self.model(**data.model_dump())
        self.session.add(instance)
        self.session.flush()
        return instance

    def get_by_id(self, entity_id: int) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def list(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        statement = (
            select(self.model)
            .order_by(*inspect(self.model).primary_key)
            .offset(offset)
            .limit(limit)
        )
        if 'auth_scope' in self.session.info:
            from app.api.auth_dependencies import scope_expression
            clause = scope_expression(self.model, *self.session.info['auth_scope'])
            if clause is not None:
                statement = statement.where(clause)
        return list(self.session.scalars(statement).all())

    def update(self, entity_id: int, data: UpdateT) -> ModelT | None:
        instance = self.get_by_id(entity_id)
        if instance is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(instance, field, value)
        self.session.flush()
        return instance

    def delete(self, entity_id: int) -> bool:
        instance = self.get_by_id(entity_id)
        if instance is None:
            return False
        self.session.delete(instance)
        self.session.flush()
        return True
