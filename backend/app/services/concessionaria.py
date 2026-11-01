from app.models.concessionaria import Concessionaria
from app.repositories.concessionaria import ConcessionariaRepository
from app.schemas.concessionaria import ConcessionariaCreate, ConcessionariaUpdate
from app.services.base import BaseService


class ConcessionariaService(BaseService[Concessionaria, ConcessionariaCreate, ConcessionariaUpdate]):
    revalida_contexto_documental = True
    repository_class = ConcessionariaRepository
