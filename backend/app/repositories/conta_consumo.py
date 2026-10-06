from app.models.conta_consumo import ContaConsumo
from app.repositories.base import BaseRepository
from app.schemas.conta_consumo import ContaConsumoCreate, ContaConsumoUpdate


class ContaConsumoRepository(
    BaseRepository[ContaConsumo, ContaConsumoCreate, ContaConsumoUpdate]
):
    model = ContaConsumo
