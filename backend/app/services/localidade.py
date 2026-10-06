from app.models.localidade import Localidade
from app.repositories.localidade import LocalidadeRepository
from app.schemas.localidade import LocalidadeCreate, LocalidadeUpdate
from app.services.base import BaseService


class LocalidadeService(BaseService[Localidade, LocalidadeCreate, LocalidadeUpdate]):
    repository_class = LocalidadeRepository
