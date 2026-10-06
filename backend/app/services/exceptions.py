class EntityNotFoundError(LookupError):
    """Registro ausente, traduzível em HTTP 404 pela camada de rotas."""

    def __init__(self, entity: str, entity_id: int | None) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} com ID {entity_id} não encontrado")
