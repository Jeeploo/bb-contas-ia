from app.models.base import Base
from app.models.concessionaria import Concessionaria
from app.models.conta_consumo import ContaConsumo
from app.models.dado_extraido import DadoExtraido
from app.models.documento import Documento
from app.models.extracao_inteligente import ExtracaoInteligente
from app.models.localidade import Localidade
from app.models.prefixo import Prefixo

__all__ = [
    "Base",
    "Concessionaria",
    "ContaConsumo",
    "DadoExtraido",
    "Documento",
    "ExtracaoInteligente",
    "Localidade",
    "Prefixo",
]
