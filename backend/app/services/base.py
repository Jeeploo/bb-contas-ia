from typing import Generic

from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository, CreateT, ModelT, UpdateT
from app.services.exceptions import EntityNotFoundError


class BaseService(Generic[ModelT, CreateT, UpdateT]):
    """CRUD via repositories, com uma transação por operação de escrita.

    A sessão deve ser dedicada à operação: commit/rollback afetam toda a
    transação pendente. Leituras não fazem commit. Erros são propagados.
    Atualizações validam apenas FKs explicitamente enviadas, inclusive None.
    """

    repository_class: type[BaseRepository[ModelT, CreateT, UpdateT]]
    foreign_keys: dict[str, type[BaseRepository]] = {}

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = self.repository_class(session)

    def _validate_foreign_keys(self, data: CreateT | UpdateT) -> None:
        values = data.model_dump(exclude_unset=True)
        for field, repository_class in self.foreign_keys.items():
            if field in values:
                entity_id = values[field]
                if entity_id is None or repository_class(self.session).get_by_id(entity_id) is None:
                    raise EntityNotFoundError(repository_class.model.__name__, entity_id)

    def create(self, data: CreateT) -> ModelT:
        try:
            self._validate_foreign_keys(data)
            instance = self.repository.create(data)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return instance

    def get_by_id(self, entity_id: int) -> ModelT:
        instance = self.repository.get_by_id(entity_id)
        if instance is None:
            raise EntityNotFoundError(self.repository.model.__name__, entity_id)
        return instance

    def list(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        return self.repository.list(offset=offset, limit=limit)

    def update(self, entity_id: int, data: UpdateT) -> ModelT:
        try:
            self.get_by_id(entity_id)
            self._validate_foreign_keys(data)
            instance = self.repository.update(entity_id, data)
            if instance is None:
                raise EntityNotFoundError(self.repository.model.__name__, entity_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return instance

    def delete(self, entity_id: int) -> bool:
        try:
            if not self.repository.delete(entity_id):
                raise EntityNotFoundError(self.repository.model.__name__, entity_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return True
