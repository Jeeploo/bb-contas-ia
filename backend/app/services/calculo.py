from app.models.calculo import Calculo
from app.repositories.calculo import CalculoRepository
from app.repositories.conta_consumo import ContaConsumoRepository
from app.repositories.regra_calculo import RegraCalculoRepository
from app.schemas.calculo import CalculoCreate, CalculoUpdate
from app.services.base import BaseService


class CalculoService(BaseService[Calculo, CalculoCreate, CalculoUpdate]):
    repository_class = CalculoRepository
    foreign_keys = {
        "id_conta": ContaConsumoRepository,
        "id_regra": RegraCalculoRepository,
    }
