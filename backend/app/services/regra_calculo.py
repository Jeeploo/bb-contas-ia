from app.models.regra_calculo import RegraCalculo
from app.repositories.regra_calculo import RegraCalculoRepository
from app.schemas.regra_calculo import RegraCalculoCreate, RegraCalculoUpdate
from app.services.base import BaseService


class RegraCalculoService(BaseService[RegraCalculo, RegraCalculoCreate, RegraCalculoUpdate]):
    repository_class = RegraCalculoRepository
