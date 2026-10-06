from app.models.ordem_pagamento import OrdemPagamento
from app.repositories.ordem_pagamento import OrdemPagamentoRepository
from app.repositories.calculo import CalculoRepository
from app.repositories.sistema_pagamento import SistemaPagamentoRepository
from app.repositories.usuario import UsuarioRepository
from app.schemas.ordem_pagamento import OrdemPagamentoCreate, OrdemPagamentoUpdate
from app.services.base import BaseService


class OrdemPagamentoService(BaseService[OrdemPagamento, OrdemPagamentoCreate, OrdemPagamentoUpdate]):
    repository_class = OrdemPagamentoRepository
    foreign_keys = {
        "id_calculo": CalculoRepository,
        "id_sistema": SistemaPagamentoRepository,
        "id_usuario_criador": UsuarioRepository,
    }
