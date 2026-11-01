from app.models.conta_consumo import ContaConsumo
from app.repositories.conta_consumo import ContaConsumoRepository
from app.repositories.prefixo import PrefixoRepository
from app.repositories.concessionaria import ConcessionariaRepository
from app.schemas.conta_consumo import ContaConsumoCreate, ContaConsumoUpdate
from app.services.base import BaseService


class ContaConsumoService(BaseService[ContaConsumo, ContaConsumoCreate, ContaConsumoUpdate]):
    revalida_contexto_documental = True
    repository_class = ContaConsumoRepository
    foreign_keys = {
        "id_prefixo": PrefixoRepository,
        "id_concessionaria": ConcessionariaRepository,
    }
