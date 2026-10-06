from app.models.concessionaria import Concessionaria
from app.repositories.concessionaria import ConcessionariaRepository
from app.schemas.concessionaria import ConcessionariaCreate, ConcessionariaUpdate
from app.services.base import BaseService


class ConcessionariaService(BaseService[Concessionaria, ConcessionariaCreate, ConcessionariaUpdate]):
    repository_class = ConcessionariaRepository
