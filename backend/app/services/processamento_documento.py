from dataclasses import replace, asdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import BinaryIO

from app.models.perfil_processamento import PerfilProcessamento
from sqlalchemy import select
from app.processing.structured import StructuredDocumentExtractor, DeterministicStructuredExtractor
from app.repositories.item_extraido import ItemExtraidoRepository
from app.schemas.item_extraido import ItemExtraidoCreate
from app.models.documento import Documento
from app.models.extracao_inteligente import ExtracaoInteligente

from sqlalchemy.orm import Session

from app.core.config import settings
from app.processing.storage import (DocumentStorage, get_document_storage, storage_for_document, document_storage_key)
from app.processing.text import DocumentTextExtractor
from app.processing.ocr import HybridPdfTextExtractor
from app.processing.fields import FieldExtractor
from app.repositories.conta_consumo import ContaConsumoRepository
from app.repositories.documento import DocumentoRepository
from app.repositories.extracao_inteligente import ExtracaoInteligenteRepository
from app.repositories.dado_extraido import DadoExtraidoRepository
from app.schemas.documento import DocumentoCreate
from app.schemas.extracao_inteligente import ExtracaoInteligenteCreate
from app.schemas.dado_extraido import DadoExtraidoCreate
from app.schemas.processamento_documento import ProcessamentoDocumentoRead
from app.services.exceptions import EntityNotFoundError, InvalidPdfError, UnsupportedDocumentFormatError


class ProcessamentoDocumentoService:
    """Uma transação por escrita, com componentes substituíveis por injeção."""
    def __init__(self, session: Session, storage: DocumentStorage | None = None,
                 text_extractor: DocumentTextExtractor | None = None,
                 field_extractor: FieldExtractor | None = None,
                 structured_extractor: StructuredDocumentExtractor | None = None):
        self.session = session
        self.storage = storage  # Override para testes; o default é resolvido por operação/documento.
        self.text_extractor = text_extractor or HybridPdfTextExtractor(max_pages=settings.max_ocr_pages)
        self.field_extractor = field_extractor
        self.structured_extractor = structured_extractor or DeterministicStructuredExtractor()
        self.documents = DocumentoRepository(session)
        self.extractions = ExtracaoInteligenteRepository(session)
        self.fields = DadoExtraidoRepository(session)

    def upload(self, account_id: int, source: BinaryIO, filename: str,
               content_type: str, contexto=None) -> Documento:
        key = None
        try:
            if ContaConsumoRepository(self.session).get_by_id(account_id) is None:
                raise EntityNotFoundError("ContaConsumo", account_id)
            if contexto is not None:
                from app.services.contexto_operacional import ContextoOperacionalService
                from app.services.exceptions import ContextoOperacionalError
                prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
                if prefix.id_prefixo != ContaConsumoRepository(self.session).get_by_id(account_id).id_prefixo:
                    raise ContextoOperacionalError("Prefixo não corresponde à conta")
            storage = self.storage if self.storage is not None else get_document_storage()
            key = storage.save(source, filename, content_type)
            document = self.documents.create(DocumentoCreate(
                tipo_documento="fatura", formato=filename.rsplit(".", 1)[-1].lower(), origem="upload",
                data_recebimento=datetime.now(timezone.utc).replace(tzinfo=None), caminho_arquivo=key,
                id_conta=account_id))
            document.storage_provider = storage.provider
            document.storage_key = key
            self.session.commit()
        except Exception:
            self.session.rollback()
            if key is not None:
                try:
                    storage.delete(key)
                except Exception:
                    # Não esconder a causa da falha transacional nem vazar erro do SDK.
                    import logging
                    logging.getLogger(__name__).warning('document_storage_cleanup_failed')
            raise
        return document

    def upload_inicial(self, source, filename, content_type, contexto):
        from app.services.contexto_operacional import ContextoOperacionalService
        from app.services.exceptions import ContextoOperacionalError
        if contexto is None:
            raise ContextoOperacionalError("Upload exige contexto de usuário")
        prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
        key = None
        try:
            storage = self.storage if self.storage is not None else get_document_storage()
            key = storage.save(source, filename, content_type)
            document = Documento(tipo_documento="fatura", formato=filename.rsplit(".", 1)[-1].lower(),
                origem="upload", data_recebimento=datetime.now(timezone.utc).replace(tzinfo=None),
                caminho_arquivo=key, id_prefixo_contexto=prefix.id_prefixo,
                id_usuario_contexto=contexto.id_usuario)
            document.storage_provider = storage.provider
            document.storage_key = key
            self.session.add(document)
            self.session.commit()
            return document
        except Exception:
            self.session.rollback()
            if key is not None:
                try:
                    storage.delete(key)
                except Exception:
                    # Não esconder a causa da falha transacional nem vazar erro do SDK.
                    import logging
                    logging.getLogger(__name__).warning('document_storage_cleanup_failed')
            raise

    def _response(self, document: Documento, extraction: ExtracaoInteligente) -> ProcessamentoDocumentoRead:
        return ProcessamentoDocumentoRead(
            documento=document, extracao=extraction,
            campos_encontrados=extraction.dados_extraidos,
            itens_encontrados=extraction.itens_extraidos,
            confianca_geral=extraction.nivel_confianca,
            situacao=extraction.situacao_validacao)

    def processar(self, document_id: int, contexto=None) -> ProcessamentoDocumentoRead:
        try:
            # Bloqueio de linha no PostgreSQL serializa cliques concorrentes.
            document = self.documents.get_for_processing(document_id)
            if document is None:
                raise EntityNotFoundError("Documento", document_id)
            if contexto is not None:
                from app.services.contexto_operacional import ContextoOperacionalService
                from app.services.exceptions import ContextoOperacionalError
                prefix = ContextoOperacionalService(self.session).resolver(contexto.id_usuario, contexto.id_prefixo)
                if prefix.id_prefixo != (document.conta.id_prefixo if document.conta else document.id_prefixo_contexto):
                    raise ContextoOperacionalError("Prefixo não corresponde à conta")
            if document.conta is None:
                from app.services.exceptions import ContextoOperacionalError
                raise ContextoOperacionalError("Documento inicial exige processamento inteligente")
            existing = self.extractions.get_completed_for_document(document_id)
            if existing is not None:
                if contexto is not None and (
                    existing.id_usuario_contexto != contexto.id_usuario
                    or existing.id_prefixo_contexto != prefix.id_prefixo
                ):
                    from app.services.validacao_documental import ValidacaoDocumentalService
                    ValidacaoDocumentalService(self.session).revalidar(existing, contexto)
                response = self._response(document, existing)
                self.session.commit()
                return response
            if document.formato.lower() != "pdf":
                raise UnsupportedDocumentFormatError("Somente PDF é suportado")
            result = self.text_extractor.extract(storage_for_document(document, self.storage).read(document_storage_key(document)))
            if not result.sucesso:
                raise InvalidPdfError("Extrator não concluiu a leitura do documento")
            account = document.conta
            if account is None:
                from app.services.exceptions import ContextoOperacionalError
                raise ContextoOperacionalError("Documento inicial exige processamento inteligente")
            profiles = self.session.scalars(select(PerfilProcessamento).where(
                PerfilProcessamento.id_prefixo == account.id_prefixo)).all()
            context = dict(id_prefixo=account.id_prefixo, uf=account.prefixo.localidade.estado,
                           tipo_servico=account.categoria, id_concessionaria=account.id_concessionaria,
                           perfis=[dict(id_perfil=p.id_perfil, tipo_servico=p.tipo_servico,
                                        estrategia=p.estrategia, parametros=p.parametros) for p in profiles])
            structured = self.structured_extractor.extract(result.texto, context)
            extracted_fields = self.field_extractor.extract(result.texto) if self.field_extractor else structured.campos
            items = [replace(item, nivel_confianca=min(item.nivel_confianca, Decimal(result.confianca_base)))
                     for item in structured.itens]
            fields = [replace(field, nivel_confianca=min(field.nivel_confianca, Decimal(result.confianca_base)))
                      for field in extracted_fields]
            for field in [*fields, *items]:
                if not Decimal(0) <= field.nivel_confianca <= Decimal(100):
                    raise ValueError("Confiança deve estar entre 0 e 100")
            all_values = [*fields, *items]
            confidence = (sum((value.nivel_confianca for value in all_values), Decimal(0))
                          / len(all_values)).quantize(Decimal("0.01")) if all_values else None
            extraction = self.extractions.create(ExtracaoInteligenteCreate(
                id_documento=document_id, data_processamento=datetime.now(timezone.utc).replace(tzinfo=None),
                nivel_confianca=confidence, situacao_validacao="requer_validacao"))
            for field in fields:
                self.fields.create(DadoExtraidoCreate(
                    id_extracao=extraction.id_extracao,
                    campo_identificado=field.campo_identificado,
                    valor_extraido=field.valor_extraido, nivel_confianca=field.nivel_confianca,
                    situacao_validacao="pendente"))
            for item in items:
                ItemExtraidoRepository(self.session).create(ItemExtraidoCreate(
                    id_extracao=extraction.id_extracao, **asdict(item)))
            from app.services.validacao_documental import ValidacaoDocumentalService
            ValidacaoDocumentalService(self.session).revalidar(extraction, contexto)
            response = self._response(document, extraction)
            self.session.commit()
            return response
        except Exception:
            self.session.rollback()
            raise

    def processar_inteligente(self, document_id, contexto, provider=None, reprocessar=False):
        from app.services.leitura_inteligente import LeituraInteligenteService
        return LeituraInteligenteService(self.session, self.storage, provider).processar(
            document_id, contexto, reprocessar=reprocessar)
