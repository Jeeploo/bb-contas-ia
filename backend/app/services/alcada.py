from app.models.alcada import Alcada
from app.repositories.alcada import AlcadaRepository
from app.schemas.alcada import AlcadaCreate, AlcadaUpdate
from app.services.base import BaseService


class AlcadaService(BaseService[Alcada, AlcadaCreate, AlcadaUpdate]):
    repository_class = AlcadaRepository
