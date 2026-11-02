"""Jornada documental DEMO persistida no histórico existente, sem cadastros fictícios."""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from app.models import Documento, ExtracaoInteligente, Usuario, Alcada, Calculo
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.validacao_documental import ValidacaoDocumentalService, politica_revisao, TIPOS, normalizar
from app.services.calculo_contextual import CalculoContextualService
from app.schemas.leitura_inteligente import ProcessamentoInteligenteRead
from app.services.exceptions import (ContextoOperacionalError, EntityNotFoundError,
    SelfApprovalNotAllowedError, InsufficientApprovalLimitError)


def evento(extraction, name):
    return next((h for h in reversed(extraction.historico_validacao_documental or []) if h.get('evento') == name), None)


def registrar(extraction, name, **data):
    extraction.historico_validacao_documental = [*(extraction.historico_validacao_documental or []),
        dict(evento=name, data=datetime.now(timezone.utc).isoformat(), **data)]


class JornadaDemoService:
    def __init__(self, session):
        self.session = session

    def obter(self, document_id, contexto):
        prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
        document = self.session.scalar(select(Documento).where(Documento.id_documento == document_id).with_for_update())
        if document is None:
            raise EntityNotFoundError('Documento', document_id)
        if prefix.id_prefixo != (document.conta.id_prefixo if document.conta else document.id_prefixo_contexto):
            raise ContextoOperacionalError('Prefixo não autorizado')
        extraction = self.session.scalar(select(ExtracaoInteligente).where(
            ExtracaoInteligente.id_documento == document_id).order_by(ExtracaoInteligente.id_extracao.desc()).with_for_update())
        return document, extraction, prefix

    def calculo_persistido(self, document, extraction):
        if extraction is None:
            return None
        snapshot = evento(extraction, 'CALCULO_DEMO')
        if snapshot:
            return snapshot['calculo']
        # Recupera também resultados do caminho anterior, vinculados à extração exata.
        if document.id_conta is not None:
            calculations = self.session.scalars(select(Calculo).where(
                Calculo.id_conta == document.id_conta, Calculo.situacao == 'validado').order_by(Calculo.id_calculo.desc()))
            for calculation in calculations:
                if (calculation.memoria_calculo or {}).get('id_extracao') == extraction.id_extracao:
                    from app.schemas.calculo import CalculoRead
                    return CalculoRead.model_validate(calculation).model_dump(mode='json')
        return None

    def resposta(self, document, extraction):
        return dict(documento=document, processamento=ProcessamentoInteligenteRead(documento=document, extracao=extraction,
                campos_encontrados=extraction.dados_extraidos, itens_encontrados=extraction.itens_extraidos,
                confianca_geral=extraction.nivel_confianca, situacao=extraction.situacao_validacao,
                metadados_ia=extraction.metadados_ia or {}) if extraction else None,
            calculo=self.calculo_persistido(document, extraction))

    def retomar(self, contexto):
        prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
        documents = self.session.scalars(select(Documento).where(
            Documento.id_usuario_contexto == contexto.id_usuario,
            Documento.id_prefixo_contexto == prefix.id_prefixo).order_by(Documento.id_documento.desc()).limit(1)).all()
        for document in documents:
            if document.origem == 'upload_encerrado':
                return dict(documento=None, processamento=None, calculo=None)
            extraction = self.session.scalar(select(ExtracaoInteligente).where(
                ExtracaoInteligente.id_documento == document.id_documento).order_by(ExtracaoInteligente.id_extracao.desc()))
            # Encerrar a jornada visual nunca apaga o documento nem volta a jornadas anteriores.
            if extraction and evento(extraction, 'NOVA_FATURA'):
                return dict(documento=None, processamento=None, calculo=None)
            if extraction and extraction.evidencias_validacao_documental.get('versao_validador', 0) < 3:
                ValidacaoDocumentalService(self.session).revalidar(extraction)
                self.session.commit()
            return self.resposta(document, extraction)
        return dict(documento=None, processamento=None, calculo=None)

    def calcular(self, document_id, contexto):
        try:
            document, extraction, prefix = self.obter(document_id, contexto)
            if extraction is None or not evento(extraction, 'ENVIADO_PARA_VALIDACAO'):
                raise ContextoOperacionalError('Envie o documento para validação antes do cálculo')
            existing = evento(extraction, 'CALCULO_DEMO')
            if existing:
                return existing['calculo']
            ValidacaoDocumentalService(self.session).revalidar(extraction)
            if politica_revisao(extraction)['bloqueia_calculo']:
                raise ContextoOperacionalError('Documento possui erro bloqueante')
            if any(f.situacao_validacao != 'validada' for f in extraction.dados_extraidos):
                raise ContextoOperacionalError('Confirme todos os dados documentais')
            existing = evento(extraction, 'CALCULO_DEMO')
            if existing:
                return existing['calculo']
            values = extraction.evidencias_validacao_documental['dados_identificados']
            from app.core.config import settings
            base, rule, memory = CalculoContextualService(self.session).executar(extraction, prefix,
                TIPOS[normalizar(values['tipo_documento'])], extraction.evidencias_validacao_documental.get('id_concessionaria'), demo=settings.demo_mode)
            memory['pendencias'] = politica_revisao(extraction)['pendencias']
            calculation = dict(id_extracao=extraction.id_extracao, id_conta=document.id_conta,
                id_regra=rule.id_regra if rule else None, data_calculo=datetime.now(timezone.utc).isoformat(),
                valor_inicial=str(base), valor_calculado=memory['resultado'],
                memoria_calculo=memory, situacao='validado', origem='documental_demo')
            registrar(extraction, 'CALCULO_DEMO', calculo=calculation, id_usuario=contexto.id_usuario)
            extraction.situacao_validacao = 'processamento_concluido'
            if document.conta:
                document.conta.situacao = 'pronta_checker'
            self.session.commit()
            return calculation
        except Exception:
            self.session.rollback()
            raise

    def confirmar(self, document_id, contexto, valores, enviar):
        from app.schemas.dado_extraido import DadoExtraidoValidacao
        from app.schemas.item_extraido import ItemExtraidoValidacao
        from app.services.dado_extraido import DadoExtraidoService
        from app.services.item_extraido import ItemExtraidoService
        from app.services.validacao_documental import encaminhar_revisao
        from app.services.conta_consumo import ContaConsumoService
        try:
            document, extraction, _ = self.obter(document_id, contexto)
            if extraction is None or evento(extraction, 'CALCULO_DEMO'):
                raise ContextoOperacionalError('Documento sem leitura editável')
            for field in extraction.dados_extraidos:
                key = 'd' + str(field.id_dado_extraido)
                data = DadoExtraidoValidacao(**({'valor_validado': valores[key]} if key in valores else
                    {'valor_validado': field.valor_validado} if field.valor_validado is not None else {}))
                DadoExtraidoService(self.session).validar(field.id_dado_extraido, data, defer=True)
            for item in extraction.itens_extraidos:
                key = 'i' + str(item.id_item_extraido)
                data = ItemExtraidoValidacao(**({'valor_validado': valores[key]} if key in valores else
                    {'valor_validado': item.valor_validado} if item.valor_validado is not None else {}))
                ItemExtraidoService(self.session).validar(item.id_item_extraido, data, defer=True)
            if enviar:
                encaminhar_revisao(self.session, extraction, contexto)
            else:
                ValidacaoDocumentalService(self.session).revalidar(extraction, contexto)
            ContaConsumoService(self.session).criar_da_leitura(extraction)
            self.session.commit()
            return self.resposta(document, extraction)
        except Exception:
            self.session.rollback()
            raise

    def nova(self, document_id, contexto):
        document, extraction, _ = self.obter(document_id, contexto)
        if document.id_usuario_contexto != contexto.id_usuario:
            raise ContextoOperacionalError('Jornada pertence a outro usuário')
        if extraction:
            registrar(extraction, 'NOVA_FATURA', id_usuario=contexto.id_usuario)
        else:
            # Upload sem leitura continua no histórico, mas deixa de ser contexto visual.
            document.origem = 'upload_encerrado'
        self.session.commit()

    def fila(self, contexto):
        prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
        extractions = self.session.scalars(select(ExtracaoInteligente).where(
            ExtracaoInteligente.id_prefixo_contexto == prefix.id_prefixo,
            ExtracaoInteligente.situacao_validacao.in_(['processamento_concluido', 'confirmada_checker', 'rejeitada_checker']))).all()
        return [self.resposta(e.documento, e) for e in extractions if evento(e, 'CALCULO_DEMO')]

    def decidir(self, document_id, contexto, decisao, observacao):
        try:
            document, extraction, _ = self.obter(document_id, contexto)
            if not extraction or extraction.situacao_validacao != 'processamento_concluido':
                raise ContextoOperacionalError('Fatura não está disponível para decisão')
            calculation = evento(extraction, 'CALCULO_DEMO')
            if not calculation:
                raise ContextoOperacionalError('Fatura sem cálculo válido')
            if calculation['id_usuario'] == contexto.id_usuario:
                raise SelfApprovalNotAllowedError('O criador não pode decidir sobre a própria fatura')
            if decisao == 'aprovado':
                ValidacaoDocumentalService(self.session).revalidar(extraction)
                if politica_revisao(extraction)['bloqueia_calculo']:
                    raise ContextoOperacionalError('Documento possui erro bloqueante')
                user = self.session.get(Usuario, contexto.id_usuario)
                limit = self.session.get(Alcada, user.id_alcada) if user.id_alcada else None
                if limit is None or limit.limite_financeiro < Decimal(calculation['calculo']['valor_calculado']):
                    raise InsufficientApprovalLimitError('Alçada financeira inferior ao valor da fatura')
            registrar(extraction, 'DECISAO_CHECKER', id_usuario=contexto.id_usuario, decisao=decisao, observacao=observacao)
            extraction.situacao_validacao = 'confirmada_checker' if decisao == 'aprovado' else 'rejeitada_checker'
            if document.conta:
                document.conta.situacao = extraction.situacao_validacao
            self.session.commit()
            return self.resposta(document, extraction)
        except Exception:
            self.session.rollback()
            raise
