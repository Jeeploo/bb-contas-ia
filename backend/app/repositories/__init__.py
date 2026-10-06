from app.repositories.alcada import AlcadaRepository
from app.repositories.usuario import UsuarioRepository
from app.repositories.sistema_pagamento import SistemaPagamentoRepository
from app.repositories.ordem_pagamento import OrdemPagamentoRepository
from app.repositories.item_pagamento import ItemPagamentoRepository
from app.repositories.aprovacao import AprovacaoRepository
from app.repositories.localidade import LocalidadeRepository
from app.repositories.prefixo import PrefixoRepository
from app.repositories.concessionaria import ConcessionariaRepository
from app.repositories.conta_consumo import ContaConsumoRepository
from app.repositories.documento import DocumentoRepository
from app.repositories.extracao_inteligente import ExtracaoInteligenteRepository
from app.repositories.dado_extraido import DadoExtraidoRepository
from app.repositories.regra_calculo import RegraCalculoRepository
from app.repositories.item_regra import ItemRegraRepository
from app.repositories.calculo import CalculoRepository

__all__ = [
    "LocalidadeRepository",
    "PrefixoRepository",
    "ConcessionariaRepository",
    "ContaConsumoRepository",
    "DocumentoRepository",
    "ExtracaoInteligenteRepository",
    "DadoExtraidoRepository",
    "RegraCalculoRepository",
    "ItemRegraRepository",
    "CalculoRepository",
    "AlcadaRepository",
    "UsuarioRepository",
    "SistemaPagamentoRepository",
    "OrdemPagamentoRepository",
    "ItemPagamentoRepository",
    "AprovacaoRepository",
]
