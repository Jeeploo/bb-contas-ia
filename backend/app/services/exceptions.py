class EntityNotFoundError(LookupError):
    """Registro ausente, traduzível em HTTP 404 pela camada de rotas."""

    def __init__(self, entity: str, entity_id: int | None) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} com ID {entity_id} não encontrado")


class SelfApprovalNotAllowedError(ValueError):
    """O criador não pode aprovar nem rejeitar a própria ordem."""


class InsufficientApprovalLimitError(ValueError):
    """Usuário sem alçada suficiente para aprovar a ordem."""


class ApprovalOrderChangeNotAllowedError(ValueError):
    """Uma aprovação registrada não pode ser transferida para outra ordem."""


class DocumentError(ValueError):
    """Falha de domínio no fluxo de documentos."""


class DocumentFileNotFoundError(DocumentError):
    """Arquivo do documento ausente no armazenamento."""


class InvalidPdfError(DocumentError):
    """PDF malformado ou protegido e não legível."""


class PdfWithoutTextError(DocumentError):
    """PDF necessita OCR ou tratamento manual."""


class UnsupportedDocumentFormatError(DocumentError):
    """Formato ou caminho fora do armazenamento suportado."""


class DocumentTooLargeError(DocumentError):
    """Arquivo excede o limite configurado."""


class EmptyDocumentError(DocumentError):
    """Upload sem conteúdo."""


class TesseractUnavailableError(DocumentError):
    """Executável Tesseract indisponível."""


class OcrLanguageUnavailableError(DocumentError):
    """Nenhum idioma OCR suportado instalado."""


class OcrPageLimitExceededError(DocumentError):
    """PDF excede o limite de páginas de OCR."""


class PdfRenderingError(DocumentError):
    """Falha ao renderizar páginas para OCR."""


class EmptyOcrError(DocumentError):
    """OCR não produziu texto utilizável."""


class OcrExecutionError(DocumentError):
    """Falha na execução local do OCR."""


class CalculationError(ValueError):
    """Configuração ou validação insuficiente para calcular."""
