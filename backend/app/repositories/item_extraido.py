from app.models.item_extraido import ItemExtraido
from app.schemas.item_extraido import ItemExtraidoCreate, ItemExtraidoValidacao
from app.repositories.base import BaseRepository


class ItemExtraidoRepository(BaseRepository[ItemExtraido, ItemExtraidoCreate, ItemExtraidoValidacao]):
    model = ItemExtraido
