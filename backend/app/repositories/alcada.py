from app.models.alcada import Alcada
from app.repositories.base import BaseRepository
from app.schemas.alcada import AlcadaCreate, AlcadaUpdate


class AlcadaRepository(BaseRepository[Alcada, AlcadaCreate, AlcadaUpdate]):
    model = Alcada
