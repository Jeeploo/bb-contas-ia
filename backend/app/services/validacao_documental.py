"""Decisão determinística. Valores do cadastro nunca substituem evidências ausentes."""
from datetime import datetime, timezone
import unicodedata
from sqlalchemy import select
from app.core.config import settings
from app.models import ExtracaoInteligente, Concessionaria, UnidadeConsumidora
from app.schemas.leitura_documental import ResultadoDocumental as R, LeituraDocumental
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.exceptions import ContextoOperacionalError, EntityNotFoundError


def normalizar(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFD", str(value or ""))
                            if not unicodedata.combining(c)).upper().split())


UFS = frozenset("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())

TIPOS = {"ENERGIA": "energia", "CONTA_ENERGIA": "energia", "AGUA": "agua", "CONTA_AGUA": "agua", "AGUA_SANEAMENTO": "agua"}


class ValidacaoDocumentalService:
    def __init__(self, session):
        self.session = session

    def avaliar(self, dados, id_usuario=None, id_prefixo=None, id_prefixo_conta=None):
        e = dict(dados_identificados=dict(dados), id_usuario=id_usuario,
                 id_prefixo_solicitado=id_prefixo, uf_mvp=settings.uf_mvp,
                 versao_validador=1)
        def result(status, reason):
            return status.value, reason, e
        tipo = normalizar(dados.get("tipo_documento"))
        if not tipo or tipo in {"DESCONHECIDO", "INDETERMINADO", "FATURA", "CONTA_CONSUMO"}:
            return result(R.EVIDENCIA_INSUFICIENTE, "Tipo documental não confirmado")
        service = TIPOS.get(tipo)
        if service is None:
            return result(R.DOCUMENTO_NAO_SUPORTADO, "Documento não identificado como conta de energia ou água")
        uf = normalizar(dados.get("uf"))
        if uf not in UFS:
            return result(R.EVIDENCIA_INSUFICIENTE, "UF ausente ou inválida")
        if uf != settings.uf_mvp:
            return result(R.REGIAO_NAO_SUPORTADA, "UF identificada fora do escopo do MVP")
        if id_usuario is None:
            return result(R.EVIDENCIA_INSUFICIENTE, "Contexto de usuário ausente")
        try:
            prefix = ContextoOperacionalService(self.session).resolver(id_usuario, id_prefixo)
        except (ContextoOperacionalError, EntityNotFoundError) as exc:
            return result(R.EVIDENCIA_INSUFICIENTE, str(exc))
        e.update(prefixo_contexto=prefix.id_prefixo, codigo_prefixo=prefix.codigo_prefixo,
                 id_localidade=prefix.id_localidade, uf_prefixo=prefix.localidade.estado,
                 municipio_prefixo=prefix.localidade.municipio)
        if id_prefixo_conta is not None and prefix.id_prefixo != id_prefixo_conta:
            return result(R.DIVERGENCIA_PREFIXO, "Contexto diferente do prefixo da conta")
        if normalizar(prefix.localidade.estado) != uf:
            return result(R.DIVERGENCIA_PREFIXO, "UF incompatível com o prefixo")
        municipio = normalizar(dados.get("municipio"))
        if not municipio:
            return result(R.EVIDENCIA_INSUFICIENTE, "Município ausente")
        if municipio != normalizar(prefix.localidade.municipio):
            return result(R.DIVERGENCIA_PREFIXO, "Município incompatível com o prefixo")
        nome = normalizar(dados.get("concessionaria"))
        if not nome:
            return result(R.EVIDENCIA_INSUFICIENTE, "Concessionária ausente")
        matches = [c for c in self.session.scalars(select(Concessionaria))
                   if nome in {normalizar(c.cnpj), normalizar(c.razao_social), normalizar(c.nome_fantasia)}]
        if len(matches) != 1:
            return result(R.EVIDENCIA_INSUFICIENTE, "Concessionária sem correspondência cadastral unívoca")
        concessionaria = matches[0]
        e["id_concessionaria"] = concessionaria.id_concessionaria
        if normalizar(concessionaria.tipo_servico) != normalizar(service):
            return result(R.EVIDENCIA_INSUFICIENTE, "Tipo documental e serviço cadastrado inconsistentes")
        unidade = str(dados.get("unidade_consumidora") or "").strip()
        if not unidade:
            return result(R.EVIDENCIA_INSUFICIENTE, "Unidade consumidora ausente")
        # Identificador exato, mantendo zeros à esquerda; endereço não prova vínculo.
        unit = self.session.scalar(select(UnidadeConsumidora).where(
            UnidadeConsumidora.id_concessionaria == concessionaria.id_concessionaria,
            UnidadeConsumidora.unidade_consumidora == unidade,
            UnidadeConsumidora.ativo.is_(True)))
        if unit is None:
            return result(R.EVIDENCIA_INSUFICIENTE, "Unidade sem vínculo cadastral ativo")
        e.update(id_unidade_consumidora=unit.id_unidade_consumidora,
                 prefixo_unidade=unit.id_prefixo, compatibilidade_unidade=unit.id_prefixo == prefix.id_prefixo)
        if unit.id_prefixo != prefix.id_prefixo:
            return result(R.DIVERGENCIA_PREFIXO, "Unidade vinculada a outro prefixo")
        return result(R.VALIDO, "Tipo, região, usuário e unidade compatíveis")

    def revalidar(self, extraction, contexto=None):
        if contexto is not None:
            prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
            if prefix.id_prefixo != (extraction.documento.conta.id_prefixo if extraction.documento.conta else extraction.documento.id_prefixo_contexto):
                raise ContextoOperacionalError("Prefixo selecionado diferente do prefixo da conta")
            extraction.id_usuario_contexto = contexto.id_usuario
            extraction.id_prefixo_contexto = prefix.id_prefixo
        dados = {}
        duplicated = False
        for field in extraction.dados_extraidos:
            if field.campo_identificado in dados:
                duplicated = True
            dados[field.campo_identificado] = (field.valor_validado
                if field.situacao_validacao == "validada" and field.valor_validado is not None else (field.valor_normalizado if field.valor_normalizado is not None else field.valor_extraido))
        status, reason, evidence = self.avaliar(dados, extraction.id_usuario_contexto,
            extraction.id_prefixo_contexto, extraction.documento.conta.id_prefixo if extraction.documento.conta else extraction.documento.id_prefixo_contexto)
        if duplicated:
            status, reason = R.EVIDENCIA_INSUFICIENTE.value, "Campos duplicados na extração"
        evidence["origens"] = {f.campo_identificado: {"id_dado_extraido": f.id_dado_extraido,
            "valor_extraido": f.valor_extraido, "valor_normalizado": f.valor_normalizado, "valor_validado": f.valor_validado,
            "situacao_validacao": f.situacao_validacao} for f in extraction.dados_extraidos}
        extraction.resultado_validacao_documental = status
        extraction.motivo_validacao_documental = reason
        extraction.evidencias_validacao_documental = evidence
        extraction.historico_validacao_documental = [*(extraction.historico_validacao_documental or []),
            dict(data=datetime.now(timezone.utc).isoformat(), resultado=status, motivo=reason, evidencias=evidence)]
        self.session.flush()
        return extraction


def revalidar_contextos(session):
    for extraction in session.scalars(select(ExtracaoInteligente).where(
            ExtracaoInteligente.id_usuario_contexto.is_not(None)).with_for_update()).all():
        session.expire(extraction, ["dados_extraidos", "documento"])
        ValidacaoDocumentalService(session).revalidar(extraction)
