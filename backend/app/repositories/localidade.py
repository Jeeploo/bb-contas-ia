from app.models.localidade import Localidade
from app.repositories.base import BaseRepository
from app.schemas.localidade import LocalidadeCreate, LocalidadeUpdate


class LocalidadeRepository(
    BaseRepository[Localidade, LocalidadeCreate, LocalidadeUpdate]
):
    model = Localidade
