"""Configuração explícita de uma regra DEMO para um prefixo e uma competência."""
import calendar
import re
from datetime import date
from sqlalchemy import select
from app.models import Documento, ExtracaoInteligente, PerfilProcessamento, Prefixo, RegraCalculo
from app.services.exceptions import CalculationError, EntityNotFoundError
from app.services.validacao_documental import TIPOS, normalizar

NOME_REGRA = 'Regra DEMO — Coeficiente 0,9055'
COEFICIENTE = '0.9055'
AVISO_DEMO = ('Regra demonstrativa baseada em um caso real de prefixo específico. '
              'Não representa uma regra financeira aplicável a todos os prefixos do Banco do Brasil.')


def configurar_regra_demo(session, document_id):
    """Não altera perfis/regras existentes. Commit pertence ao chamador."""
    document = session.get(Documento, document_id)
    if document is None:
        raise EntityNotFoundError('Documento', document_id)
    prefix_id = document.id_prefixo_contexto or (document.conta.id_prefixo if document.conta else None)
    prefix = session.scalar(select(Prefixo).where(Prefixo.id_prefixo == prefix_id).with_for_update())
    if prefix is None:
        raise CalculationError('Documento sem prefixo definido')
    extraction = session.scalar(select(ExtracaoInteligente).where(
        ExtracaoInteligente.id_documento == document_id).order_by(ExtracaoInteligente.id_extracao.desc()))
    if extraction is None:
        raise CalculationError('Documento sem leitura persistida')
    values = {f.campo_identificado: f.valor_validado if f.valor_validado is not None else
              f.valor_normalizado if f.valor_normalizado is not None else f.valor_extraido
              for f in extraction.dados_extraidos}
    competence = values.get('competencia') or ''
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', competence):
        raise CalculationError('Competência documental inválida')
    category = TIPOS.get(normalizar(values.get('tipo_documento')))
    if category is None:
        raise CalculationError('Tipo documental não suportado')
    start = date.fromisoformat(competence + '-01')
    end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
    parameters = dict(coeficiente=COEFICIENTE, arredondamento='ROUND_HALF_UP', demonstrativa=True,
                      escopo_demo=dict(id_prefixo=prefix.id_prefixo, competencia=competence), aviso_demo=AVISO_DEMO)
    profiles = session.scalars(select(PerfilProcessamento).where(
        PerfilProcessamento.id_prefixo == prefix.id_prefixo,
        PerfilProcessamento.situacao == 'ativo', PerfilProcessamento.data_inicio_vigencia <= end,
        (PerfilProcessamento.data_fim_vigencia.is_(None) | (PerfilProcessamento.data_fim_vigencia >= start)))).all()
    if profiles:
        profile = profiles[0]
        rule = session.get(RegraCalculo, profile.id_regra)
        if (len(profiles) == 1 and profile.parametros == parameters and profile.estrategia == 'COEFICIENTE'
                and profile.tipo_servico == category and profile.id_concessionaria is None
                and profile.data_inicio_vigencia == start and profile.data_fim_vigencia == end
                and rule and rule.nome_regra == NOME_REGRA and rule.situacao == 'ativa'
                and rule.categoria == category and rule.data_inicio_vigencia == start and rule.data_fim_vigencia == end):
            return profile
        raise CalculationError('Já existe perfil financeiro vigente; configuração preservada')
    rule = RegraCalculo(nome_regra=NOME_REGRA, categoria=category, versao='demo-0.9055-v1',
        data_inicio_vigencia=start, data_fim_vigencia=end, situacao='ativa')
    session.add(rule)
    session.flush()
    profile = PerfilProcessamento(id_prefixo=prefix.id_prefixo, tipo_servico=category,
        estrategia='COEFICIENTE', id_regra=rule.id_regra, id_concessionaria=None,
        situacao='ativo', data_inicio_vigencia=start, data_fim_vigencia=end, parametros=parameters)
    session.add(profile)
    session.flush()
    return profile
