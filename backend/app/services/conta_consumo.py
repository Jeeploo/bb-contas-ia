from app.models.conta_consumo import ContaConsumo
from app.repositories.conta_consumo import ContaConsumoRepository
from app.repositories.prefixo import PrefixoRepository
from app.repositories.concessionaria import ConcessionariaRepository
from app.schemas.conta_consumo import ContaConsumoCreate, ContaConsumoUpdate
from app.services.base import BaseService


class ContaConsumoService(BaseService[ContaConsumo, ContaConsumoCreate, ContaConsumoUpdate]):
    revalida_contexto_documental = True
    repository_class = ContaConsumoRepository
    foreign_keys = {
        "id_prefixo": PrefixoRepository,
        "id_concessionaria": ConcessionariaRepository,
    }

    def criar_da_leitura(self, extraction):
        """Somente evidência validada cria conta; documento bloqueado permanece em revisão.

        O lock do documento na orquestração torna reprocessamentos idempotentes.
        Não atualiza contas preexistentes nem usa valores cadastrais como extração.
        """
        document = extraction.documento
        if document.id_conta is not None or extraction.resultado_validacao_documental != "VALIDO":
            return document.conta
        from datetime import date
        from decimal import Decimal
        from app.services.validacao_documental import TIPOS, normalizar
        values = {f.campo_identificado: (f.valor_validado if f.valor_validado is not None
                  else f.valor_normalizado if f.valor_normalizado is not None else f.valor_extraido)
                  for f in extraction.dados_extraidos}
        if any(not values.get(key) for key in ("competencia", "data_vencimento", "valor_original")):
            return None
        import re
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", values["competencia"]):
            return None
        account = ContaConsumo(
            numero_conta=values.get("unidade_consumidora"), competencia=values["competencia"],
            data_emissao=date.fromisoformat(values["data_emissao"]) if values.get("data_emissao") else None,
            data_vencimento=date.fromisoformat(values["data_vencimento"]),
            valor_original=Decimal(values["valor_original"]), codigo_barras=values.get("codigo_barras"),
            consumo=Decimal(values["consumo"]) if values.get("consumo") is not None else None,
            unidade_consumo=values.get("unidade_consumo"), categoria=TIPOS[normalizar(values["tipo_documento"])],
            situacao="pendente", id_prefixo=extraction.id_prefixo_contexto,
            id_concessionaria=extraction.evidencias_validacao_documental["id_concessionaria"])
        self.session.add(account)
        document.conta = account
        self.session.flush()
        return account
