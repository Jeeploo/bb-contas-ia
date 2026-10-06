from app.models.sistema_pagamento import SistemaPagamento
from app.repositories.sistema_pagamento import SistemaPagamentoRepository
from app.schemas.sistema_pagamento import SistemaPagamentoCreate, SistemaPagamentoUpdate
from app.services.base import BaseService


class SistemaPagamentoService(BaseService[SistemaPagamento, SistemaPagamentoCreate, SistemaPagamentoUpdate]):
    repository_class = SistemaPagamentoRepository
