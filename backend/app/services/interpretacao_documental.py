"""Persistência do contrato de leitura; sem dependência de fornecedor ou OCR."""
from datetime import datetime, timezone
from sqlalchemy import select
from app.models import DadoExtraido, ItemExtraido, ExtracaoInteligente, Documento
from app.services.exceptions import EntityNotFoundError, ContextoOperacionalError
from app.services.validacao_documental import ValidacaoDocumentalService
from app.services.contexto_operacional import ContextoOperacionalService


COMPONENTES = {
    "tusd": "TUSD", "te": "TE", "valor_bandeira_tarifaria": "BANDEIRA",
    "iluminacao_publica": "ILUMINACAO_PUBLICA", "icms": "ICMS", "pis": "PIS",
    "cofins": "COFINS", "tarifa_agua": "TARIFA_AGUA", "tarifa_esgoto": "TARIFA_ESGOTO",
    "servicos_adicionais": "SERVICOS_ADICIONAIS", "descontos": "DESCONTO",
    "multas": "MULTA", "juros": "JUROS", "outros_encargos": "OUTROS_ENCARGOS",
}


class InterpretacaoDocumentalService:
    def __init__(self, session):
        self.session = session

    def registrar(self, document_id, leitura, contexto, *, commit=True, metadados=None, original=None):
        try:
            document = self.session.scalar(select(Documento).where(
                Documento.id_documento == document_id).with_for_update())
            if document is None:
                raise EntityNotFoundError("Documento", document_id)
            prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
            if prefix.id_prefixo != (document.conta.id_prefixo if document.conta else document.id_prefixo_contexto):
                raise ContextoOperacionalError("Prefixo selecionado diferente do prefixo da conta")
            extraction = ExtracaoInteligente(id_documento=document_id,
                data_processamento=datetime.now(timezone.utc).replace(tzinfo=None),
                situacao_validacao="requer_validacao", id_usuario_contexto=contexto.id_usuario,
                id_prefixo_contexto=prefix.id_prefixo, metadados_ia=metadados, resposta_original_ia=original)
            self.session.add(extraction)
            for name, value in leitura.dados_canonicos().items():
                if name in COMPONENTES:
                    extraction.itens_extraidos.append(ItemExtraido(categoria="tributo" if name in {"icms", "pis", "cofins"} else "componente",
                        descricao_original=name, tipo_normalizado=COMPONENTES[name], valor=value,
                        situacao_validacao="pendente"))
                else:
                    raw_name = "valor_total" if name == "valor_original" else name
                    raw = (original or {}).get(raw_name)
                    if name == "consumo" and raw is None:
                        raw = (original or {}).get("consumo_kwh")
                        if raw is None:
                            raw = (original or {}).get("consumo_m3")
                    extraction.dados_extraidos.append(DadoExtraido(campo_identificado=name,
                        valor_extraido=str(raw) if raw is not None else str(value),
                        valor_normalizado=str(value) if original is not None else None,
                        situacao_validacao="pendente"))
            self.session.flush()
            ValidacaoDocumentalService(self.session).revalidar(extraction)
            from app.services.conta_consumo import ContaConsumoService
            ContaConsumoService(self.session).criar_da_leitura(extraction)
            if commit:
                self.session.commit()
            return extraction
        except Exception:
            if commit:
                self.session.rollback()
            raise
