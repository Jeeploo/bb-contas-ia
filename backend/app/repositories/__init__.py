from app.repositories.localidade import LocalidadeRepository
from app.repositories.prefixo import PrefixoRepository
from app.repositories.concessionaria import ConcessionariaRepository
from app.repositories.conta_consumo import ContaConsumoRepository
from app.repositories.documento import DocumentoRepository
from app.repositories.extracao_inteligente import ExtracaoInteligenteRepository
from app.repositories.dado_extraido import DadoExtraidoRepository

__all__ = [
    "LocalidadeRepository",
    "PrefixoRepository",
    "ConcessionariaRepository",
    "ContaConsumoRepository",
    "DocumentoRepository",
    "ExtracaoInteligenteRepository",
    "DadoExtraidoRepository",
]
