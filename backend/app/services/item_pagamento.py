from app.models.item_pagamento import ItemPagamento
from app.repositories.item_pagamento import ItemPagamentoRepository
from app.repositories.ordem_pagamento import OrdemPagamentoRepository
from app.schemas.item_pagamento import ItemPagamentoCreate, ItemPagamentoUpdate
from app.services.base import BaseService


class ItemPagamentoService(BaseService[ItemPagamento, ItemPagamentoCreate, ItemPagamentoUpdate]):
    repository_class = ItemPagamentoRepository
    foreign_keys = {
        "id_ordem": OrdemPagamentoRepository,
    }
