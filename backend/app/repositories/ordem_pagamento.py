from app.models.ordem_pagamento import OrdemPagamento
from app.repositories.base import BaseRepository
from app.schemas.ordem_pagamento import OrdemPagamentoCreate, OrdemPagamentoUpdate


class OrdemPagamentoRepository(BaseRepository[OrdemPagamento, OrdemPagamentoCreate, OrdemPagamentoUpdate]):
    model = OrdemPagamento
