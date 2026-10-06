from app.models.calculo import Calculo
from app.repositories.base import BaseRepository
from app.schemas.calculo import CalculoCreate, CalculoUpdate


class CalculoRepository(
    BaseRepository[Calculo, CalculoCreate, CalculoUpdate]
):
    model = Calculo
