from datetime import datetime, date, timezone
from sqlalchemy import select
from app.models import ContaConsumo, Calculo, Documento, ExtracaoInteligente, PerfilProcessamento, RegraCalculo
from app.calculation.strategies import STRATEGIES, Component, decimal_value, validate_parameters
from app.services.exceptions import CalculationError, EntityNotFoundError


class CalculoContextualService:
    def __init__(self, session):
        self.session = session

    def calcular(self, account_id):
        try:
            account = self.session.scalars(select(ContaConsumo).where(
                ContaConsumo.id_conta == account_id).with_for_update()).first()
            if account is None:
                raise EntityNotFoundError("ContaConsumo", account_id)
            # Vigência é definida pela competência validada, nunca pelo relógio da execução.
            extraction = self.session.scalars(select(ExtracaoInteligente).join(Documento).where(
                Documento.id_conta == account_id).order_by(
                    ExtracaoInteligente.data_processamento.desc(), ExtracaoInteligente.id_extracao.desc())).first()
            if extraction is None:
                raise CalculationError("Conta sem extração; processe e valide o documento")
            if extraction.id_usuario_contexto is not None:
                from app.services.validacao_documental import ValidacaoDocumentalService, politica_revisao
                ValidacaoDocumentalService(self.session).revalidar(extraction)
                if politica_revisao(extraction)['bloqueia_calculo']:
                    raise CalculationError("Documento possui erro bloqueante")
            if account.concessionaria.tipo_servico != account.categoria:
                raise CalculationError("Serviço incompatível com a concessionária")
            base, rule, memory = self.executar(extraction, account.prefixo, account.categoria, account.id_concessionaria)
            calculation = Calculo(data_calculo=datetime.now(timezone.utc).replace(tzinfo=None),
                valor_inicial=base, valor_calculado=decimal_value(memory["resultado"]),
                situacao="validado", id_conta=account_id, id_regra=rule.id_regra, memoria_calculo=memory)
            self.session.add(calculation)
            self.session.flush()
            self.session.commit()
            return calculation
        except Exception:
            self.session.rollback()
            raise

    def executar(self, extraction, prefix, categoria, id_concessionaria):
        fields = {}
        for field in extraction.dados_extraidos:
            if field.campo_identificado in fields:
                raise CalculationError("Campos duplicados na extração")
            fields[field.campo_identificado] = field
        def validated(name):
            field = fields.get(name)
            if field is None or field.situacao_validacao != "validada" or not field.valor_validado:
                raise CalculationError(f"Campo obrigatório não validado: {name}")
            return field.valor_validado
        try:
            reference = date.fromisoformat(validated("competencia") + "-01")
        except ValueError:
            raise CalculationError("Competência validada deve usar AAAA-MM") from None
        profiles = self.session.scalars(select(PerfilProcessamento).where(
            PerfilProcessamento.id_prefixo == prefix.id_prefixo,
            PerfilProcessamento.situacao == "ativo",
            PerfilProcessamento.data_inicio_vigencia <= reference,
            (PerfilProcessamento.data_fim_vigencia.is_(None) | (PerfilProcessamento.data_fim_vigencia >= reference)))).all()
        if len(profiles) != 1:
            raise CalculationError("Prefixo deve ter exatamente um perfil ativo vigente na competência validada")
        profile = profiles[0]
        rule = self.session.get(RegraCalculo, profile.id_regra)
        if rule is None or rule.situacao != "ativa":
            raise CalculationError("Regra de cálculo ausente ou inativa")
        if reference < rule.data_inicio_vigencia or (rule.data_fim_vigencia and reference > rule.data_fim_vigencia):
            raise CalculationError("Regra fora da vigência da competência validada")
        if profile.tipo_servico != categoria or rule.categoria != profile.tipo_servico:
            raise CalculationError("Tipo de serviço incompatível com conta, concessionária ou regra")
        if id_concessionaria is not None and profile.id_concessionaria and profile.id_concessionaria != id_concessionaria:
            raise CalculationError("Concessionária diferente da esperada pelo perfil")
        if profile.parametros.get('demonstrativa'):
            if profile.parametros.get('escopo_demo') != dict(id_prefixo=prefix.id_prefixo, competencia=reference.strftime('%Y-%m')):
                raise CalculationError("Regra DEMO fora do prefixo ou competência específicos")
        validate_parameters(profile.estrategia, profile.parametros)
        base = decimal_value(validated("valor_original"))
        if base < 0:
            raise CalculationError("Valor base deve ser não negativo")
        components = [Component(c.id_item_extraido, c.tipo_normalizado, c.valor_validado,
                                c.situacao_validacao == "validada") for c in extraction.itens_extraidos]
        rules = [dict(tipo=i.nome_item, operacao=i.tipo_item,
                      obrigatorio=i.obrigatorio) for i in sorted(rule.itens, key=lambda i: i.ordem_aplicacao)]
        memory = STRATEGIES[profile.estrategia].execute(base, profile.parametros, components, rules)
        memory.update(nome_regra=rule.nome_regra,
                      demonstrativa=bool(profile.parametros.get('demonstrativa')),
                      aviso_demo=profile.parametros.get('aviso_demo') if profile.parametros.get('demonstrativa') else None,
                      escopo_demo=profile.parametros.get('escopo_demo') if profile.parametros.get('demonstrativa') else None,
                      correspondencia_cadastral_confirmada=id_concessionaria is not None,
                      concessionaria_perfil=profile.id_concessionaria,
                      origem_regra="perfil_vigente_prefixo", id_perfil=profile.id_perfil, id_regra=rule.id_regra, versao_regra=rule.versao,
                      id_extracao=extraction.id_extracao, competencia=reference.strftime("%Y-%m"),
                      itens_regra=rules, id_prefixo=prefix.id_prefixo,
                      localidade=dict(id_localidade=prefix.id_localidade,
                                      uf=prefix.localidade.estado))
        return base, rule, memory
