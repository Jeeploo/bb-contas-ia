"""Orquestra a interpretação externa sem enviar contexto operacional ao provider."""
from datetime import datetime, timezone
import hashlib
import logging
from sqlalchemy import select
from app.models import Documento, ExtracaoInteligente
from app.document_ai.base import DocumentAIError, InterpretacaoAI
from app.document_ai.factory import get_document_ai_provider
from app.document_ai.normalizacao import normalizar_leitura
from app.processing.arquivo_documental import MIMES, validar_arquivo
from app.processing.storage import storage_for_document, document_storage_key
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.interpretacao_documental import InterpretacaoDocumentalService
from app.services.validacao_documental import ValidacaoDocumentalService
from app.services.exceptions import EntityNotFoundError, ContextoOperacionalError, DocumentError, DocumentTooLargeError, DocumentFileNotFoundError, DocumentStorageError
from app.schemas.leitura_inteligente import ProcessamentoInteligenteRead

logger = logging.getLogger(__name__)
META_KEYS = {'provider','modelo_solicitado','modelo','response_id','data','prompt_version',
             'status','tokens_entrada','tokens_saida','tokens_total','latencia_ms','erro_tecnico'}


class LeituraInteligenteService:
    def __init__(self, session, storage=None, provider=None):
        self.session, self.storage = session, storage
        self.provider = provider or get_document_ai_provider()

    def _response(self, document, extraction):
        return ProcessamentoInteligenteRead(documento=document, extracao=extraction,
            campos_encontrados=extraction.dados_extraidos, itens_encontrados=extraction.itens_extraidos,
            confianca_geral=extraction.nivel_confianca, situacao=extraction.situacao_validacao,
            metadados_ia=extraction.metadados_ia or {})

    def processar(self, document_id, contexto, reprocessar=False):
        document = None
        try:
            document = self.session.scalar(select(Documento).where(
                Documento.id_documento == document_id).with_for_update())
            if document is None:
                raise EntityNotFoundError('Documento', document_id)
            if contexto is None:
                raise ContextoOperacionalError('Leitura inteligente exige contexto de usuário')
            prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
            if prefix.id_prefixo != (document.conta.id_prefixo if document.conta else document.id_prefixo_contexto):
                raise ContextoOperacionalError('Prefixo selecionado diferente do prefixo da conta')
            try:
                data = storage_for_document(document, self.storage).read(document_storage_key(document))
                mime = MIMES.get('.'+document.formato.lower())
                validar_arquivo(data, mime, verificar_pdf=True)
            except DocumentTooLargeError:
                raise DocumentAIError('limite_tamanho', 413) from None
            except DocumentFileNotFoundError:
                raise DocumentAIError('arquivo_indisponivel', 404) from None
            except DocumentStorageError:
                raise DocumentAIError('storage_indisponivel', 503) from None
            except DocumentError:
                raise DocumentAIError('arquivo_invalido', 422) from None
            fingerprint = hashlib.sha256(data).hexdigest()
            existing = self.session.scalar(select(ExtracaoInteligente).where(
                ExtracaoInteligente.id_documento == document_id,
                ExtracaoInteligente.metadados_ia['status'].as_string() == 'concluida').order_by(ExtracaoInteligente.id_extracao.desc()))
            if not reprocessar and existing and (existing.metadados_ia or {}).get('sha256_documento') == fingerprint:
                if existing.id_usuario_contexto != contexto.id_usuario or existing.id_prefixo_contexto != prefix.id_prefixo:
                    ValidacaoDocumentalService(self.session).revalidar(existing, contexto)
                from app.services.conta_consumo import ContaConsumoService
                ContaConsumoService(self.session).criar_da_leitura(existing)
                response = self._response(document, existing)
                self.session.commit()
                return response
            try:
                result = self.provider.interpretar_documento(data, mime)
            except DocumentError:
                raise DocumentAIError('arquivo_invalido', 422) from None
            if not isinstance(result, InterpretacaoAI):
                raise DocumentAIError('resposta_invalida')
            # Revalida o contrato na fronteira, inclusive para outros providers futuros.
            try:
                leitura = normalizar_leitura(result.original)
            except DocumentAIError as exc:
                exc.metadados = result.metadados
                raise
            if leitura != result.leitura:
                raise DocumentAIError('resposta_invalida', metadados=result.metadados)
            meta = {k:v for k,v in result.metadados.items() if k in META_KEYS}
            meta.update(provider=self.provider.provider, status='concluida', sha256_documento=fingerprint)
            extraction = InterpretacaoDocumentalService(self.session).registrar(document_id, leitura, contexto,
                commit=False, metadados=meta, original=result.original)
            document.historico_leitura_ia = [*(document.historico_leitura_ia or []),
                                           {**meta, 'id_extracao':extraction.id_extracao}]
            self.session.flush()
            response = self._response(document, extraction)
            self.session.commit()
            return response
        except DocumentAIError as exc:
            # Nada parcial é criado antes do provider/contrato. A tentativa técnica pertence
            # ao documento, não é uma extração que esconderia uma extração válida no cálculo.
            self.session.rollback()
            document = self.session.scalar(select(Documento).where(
                Documento.id_documento == document_id).with_for_update())
            if document is not None:
                meta = {k:v for k,v in exc.metadados.items() if k in META_KEYS}
                meta.update(provider=self.provider.provider, modelo_solicitado=self.provider.modelo,
                    status='erro', erro_tecnico=exc.codigo, data=datetime.now(timezone.utc).isoformat())
                document.historico_leitura_ia = [*(document.historico_leitura_ia or []),meta]
                self.session.commit()
            logger.warning('leitura_ia_falhou documento_id=%s codigo=%s', document_id, exc.codigo)
            raise
        except Exception:
            self.session.rollback()
            raise
