from datetime import datetime, timezone
from decimal import Decimal
from typing import BinaryIO

from app.models.documento import Documento
from app.models.extracao_inteligente import ExtracaoInteligente

from sqlalchemy.orm import Session

from app.core.config import settings
from app.processing.storage import DocumentStorage, LocalDocumentStorage
from app.processing.text import DocumentTextExtractor, PdfTextExtractor
from app.processing.fields import FieldExtractor, DeterministicFieldExtractor
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
                 field_extractor: FieldExtractor | None = None):
        self.session = session
        self.storage = storage or LocalDocumentStorage(
            settings.document_storage_path, settings.document_max_size_bytes)
        self.text_extractor = text_extractor or PdfTextExtractor()
        self.field_extractor = field_extractor or DeterministicFieldExtractor()
        self.documents = DocumentoRepository(session)
        self.extractions = ExtracaoInteligenteRepository(session)
        self.fields = DadoExtraidoRepository(session)

    def upload(self, account_id: int, source: BinaryIO, filename: str,
               content_type: str) -> Documento:
        key = None
        try:
            if ContaConsumoRepository(self.session).get_by_id(account_id) is None:
                raise EntityNotFoundError("ContaConsumo", account_id)
            key = self.storage.save(source, filename, content_type)
            document = self.documents.create(DocumentoCreate(
                tipo_documento="fatura", formato="pdf", origem="upload",
                data_recebimento=datetime.now(timezone.utc).replace(tzinfo=None), caminho_arquivo=key,
                id_conta=account_id))
            self.session.commit()
        except Exception:
            self.session.rollback()
            if key is not None:
                self.storage.delete(key)
            raise
        return document

    def _response(self, document: Documento, extraction: ExtracaoInteligente) -> ProcessamentoDocumentoRead:
        return ProcessamentoDocumentoRead(
            documento=document, extracao=extraction,
            campos_encontrados=extraction.dados_extraidos,
            confianca_geral=extraction.nivel_confianca,
            situacao=extraction.situacao_validacao)

    def processar(self, document_id: int) -> ProcessamentoDocumentoRead:
        try:
            # Bloqueio de linha no PostgreSQL serializa cliques concorrentes.
            document = self.documents.get_for_processing(document_id)
            if document is None:
                raise EntityNotFoundError("Documento", document_id)
            existing = self.extractions.get_completed_for_document(document_id)
            if existing is not None:
                response = self._response(document, existing)
                self.session.commit()
                return response
            if document.formato.lower() != "pdf":
                raise UnsupportedDocumentFormatError("Somente PDF é suportado")
            result = self.text_extractor.extract(self.storage.read(document.caminho_arquivo))
            if not result.sucesso:
                raise InvalidPdfError("Extrator não concluiu a leitura do documento")
            fields = self.field_extractor.extract(result.texto)
            for field in fields:
                if not Decimal(0) <= field.nivel_confianca <= Decimal(100):
                    raise ValueError("Confiança deve estar entre 0 e 100")
            confidence = (sum((field.nivel_confianca for field in fields), Decimal(0))
                          / len(fields)).quantize(Decimal("0.01")) if fields else None
            extraction = self.extractions.create(ExtracaoInteligenteCreate(
                id_documento=document_id, data_processamento=datetime.now(timezone.utc).replace(tzinfo=None),
                nivel_confianca=confidence, situacao_validacao="requer_validacao"))
            for field in fields:
                self.fields.create(DadoExtraidoCreate(
                    id_extracao=extraction.id_extracao,
                    campo_identificado=field.campo_identificado,
                    valor_extraido=field.valor_extraido, nivel_confianca=field.nivel_confianca,
                    situacao_validacao="pendente"))
            response = self._response(document, extraction)
            self.session.commit()
            return response
        except Exception:
            self.session.rollback()
            raise
