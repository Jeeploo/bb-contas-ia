from app.models.prefixo import Prefixo
from app.repositories.prefixo import PrefixoRepository
from app.repositories.localidade import LocalidadeRepository
from app.schemas.prefixo import PrefixoCreate, PrefixoUpdate
from app.services.base import BaseService


class PrefixoService(BaseService[Prefixo, PrefixoCreate, PrefixoUpdate]):
    repository_class = PrefixoRepository
    foreign_keys = {
        "id_localidade": LocalidadeRepository,
    }
