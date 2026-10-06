from app.models.item_regra import ItemRegra
from app.repositories.item_regra import ItemRegraRepository
from app.repositories.regra_calculo import RegraCalculoRepository
from app.schemas.item_regra import ItemRegraCreate, ItemRegraUpdate
from app.services.base import BaseService


class ItemRegraService(BaseService[ItemRegra, ItemRegraCreate, ItemRegraUpdate]):
    repository_class = ItemRegraRepository
    foreign_keys = {
        "id_regra": RegraCalculoRepository,
    }
