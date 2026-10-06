from app.models.item_pagamento import ItemPagamento
from app.repositories.base import BaseRepository
from app.schemas.item_pagamento import ItemPagamentoCreate, ItemPagamentoUpdate


class ItemPagamentoRepository(BaseRepository[ItemPagamento, ItemPagamentoCreate, ItemPagamentoUpdate]):
    model = ItemPagamento
