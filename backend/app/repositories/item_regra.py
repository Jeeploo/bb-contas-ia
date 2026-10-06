from app.models.item_regra import ItemRegra
from app.repositories.base import BaseRepository
from app.schemas.item_regra import ItemRegraCreate, ItemRegraUpdate


class ItemRegraRepository(
    BaseRepository[ItemRegra, ItemRegraCreate, ItemRegraUpdate]
):
    model = ItemRegra
