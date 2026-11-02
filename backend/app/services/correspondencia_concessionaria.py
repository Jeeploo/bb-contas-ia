"""Correspondência exata de nomes normalizados; nunca cria concessionárias."""
import re
import unicodedata
from sqlalchemy import select
from app.models import Concessionaria, ConcessionariaAlias


def normalizar_nome(value):
    value = "".join(c for c in unicodedata.normalize("NFD", str(value or "")) if not unicodedata.combining(c)).upper()
    # Pontos de abreviações (S.A.) não separam letras; demais sinais separam palavras.
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", value.replace(".", "")).split())


def correspondencias(session, nome):
    key = normalizar_nome(nome)
    if not key:
        return [], None
    oficiais = {c.id_concessionaria: c for c in session.scalars(select(Concessionaria).where(Concessionaria.ativo.is_(True)))
        if key in {normalizar_nome(c.razao_social), normalizar_nome(c.nome_fantasia), normalizar_nome(c.cnpj)}}
    aliases = session.scalars(select(Concessionaria).join(ConcessionariaAlias,
        ConcessionariaAlias.id_concessionaria == Concessionaria.id_concessionaria).where(
        Concessionaria.ativo.is_(True), ConcessionariaAlias.ativo.is_(True), ConcessionariaAlias.alias_normalizado == key)).all()
    matches = {**oficiais, **{c.id_concessionaria: c for c in aliases}}
    return list(matches.values()), "nome" if len(matches) == 1 and oficiais else "alias"


def associar(session, extraction, id_concessionaria, contexto):
    from datetime import datetime, timezone
    from app.services.exceptions import ContextoOperacionalError
    from app.services.validacao_documental import ValidacaoDocumentalService
    from app.services.conta_consumo import ContaConsumoService
    if extraction.situacao_validacao != "revisao_cadastral_pendente":
        raise ContextoOperacionalError("Documento não está em revisão cadastral pendente")
    concessionaria = session.get(Concessionaria, id_concessionaria)
    if concessionaria is None or not concessionaria.ativo:
        raise ContextoOperacionalError("Concessionária inexistente ou inativa")
    field = next((f for f in extraction.dados_extraidos if f.campo_identificado == "concessionaria"), None)
    nome = (field.valor_validado if field and field.valor_validado is not None else
            field.valor_normalizado if field and field.valor_normalizado is not None else field.valor_extraido if field else None)
    key = normalizar_nome(nome)
    if not key:
        raise ContextoOperacionalError("Nome extraído ausente")
    alias = session.scalar(select(ConcessionariaAlias).where(ConcessionariaAlias.alias_normalizado == key,
        ConcessionariaAlias.id_concessionaria == id_concessionaria))
    if alias is None:
        # SAVEPOINT e constraint garantem idempotência também entre documentos concorrentes.
        from sqlalchemy.exc import IntegrityError
        try:
            with session.begin_nested():
                session.add(ConcessionariaAlias(id_concessionaria=id_concessionaria, alias=nome, alias_normalizado=key))
                session.flush()
        except IntegrityError:
            alias = session.scalar(select(ConcessionariaAlias).where(ConcessionariaAlias.alias_normalizado == key,
                ConcessionariaAlias.id_concessionaria == id_concessionaria))
            if alias is None:
                raise
    if alias is not None:
        alias.ativo = True
    extraction.historico_validacao_documental = [*(extraction.historico_validacao_documental or []), dict(
        evento="CONCESSIONARIA_ASSOCIADA", origem="manual", id_usuario=contexto.id_usuario,
        data=datetime.now(timezone.utc).isoformat(), id_concessionaria=id_concessionaria,
        nome_extraido=field.valor_extraido, nome_normalizado=key, id_documento=extraction.id_documento,
        id_extracao=extraction.id_extracao)]
    session.flush()
    ValidacaoDocumentalService(session).revalidar(extraction, contexto)
    extraction.situacao_validacao = "validada" if extraction.resultado_validacao_documental == "VALIDO" else "revisao_cadastral_pendente"
    ContaConsumoService(session).criar_da_leitura(extraction)
    return extraction
