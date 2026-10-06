class EntityNotFoundError(LookupError):
    """Registro ausente, traduzível em HTTP 404 pela camada de rotas."""

    def __init__(self, entity: str, entity_id: int | None) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} com ID {entity_id} não encontrado")


class SelfApprovalNotAllowedError(ValueError):
    """O criador não pode aprovar nem rejeitar a própria ordem."""


class InsufficientApprovalLimitError(ValueError):
    """Usuário sem alçada suficiente para aprovar a ordem."""


class ApprovalOrderChangeNotAllowedError(ValueError):
    """Uma aprovação registrada não pode ser transferida para outra ordem."""
