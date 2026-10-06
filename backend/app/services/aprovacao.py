from app.models.aprovacao import Aprovacao
from app.repositories.aprovacao import AprovacaoRepository
from app.repositories.ordem_pagamento import OrdemPagamentoRepository
from app.repositories.usuario import UsuarioRepository
from app.schemas.aprovacao import AprovacaoCreate, AprovacaoUpdate
from app.services.base import BaseService


class AprovacaoService(BaseService[Aprovacao, AprovacaoCreate, AprovacaoUpdate]):
    repository_class = AprovacaoRepository
    foreign_keys = {
        "id_ordem": OrdemPagamentoRepository,
        "id_usuario": UsuarioRepository,
    }
