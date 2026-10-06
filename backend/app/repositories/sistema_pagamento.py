from app.models.sistema_pagamento import SistemaPagamento
from app.repositories.base import BaseRepository
from app.schemas.sistema_pagamento import SistemaPagamentoCreate, SistemaPagamentoUpdate


class SistemaPagamentoRepository(BaseRepository[SistemaPagamento, SistemaPagamentoCreate, SistemaPagamentoUpdate]):
    model = SistemaPagamento
