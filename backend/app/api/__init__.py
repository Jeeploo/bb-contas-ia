from fastapi import HTTPException, status
from fastapi.routing import APIRoute

from app.services.exceptions import (
    TesseractUnavailableError, OcrLanguageUnavailableError, OcrPageLimitExceededError,
    PdfRenderingError, EmptyOcrError, OcrExecutionError,
    DocumentFileNotFoundError, InvalidPdfError, PdfWithoutTextError,
    UnsupportedDocumentFormatError, DocumentTooLargeError, EmptyDocumentError,
    CalculationError,
    EntityNotFoundError, SelfApprovalNotAllowedError,
    InsufficientApprovalLimitError, ApprovalOrderChangeNotAllowedError,
)


class EntityNotFoundRoute(APIRoute):
    """Traduz exceções de domínio exclusivamente na camada HTTP."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request):
            try:
                return await handler(request)
            except (TesseractUnavailableError, OcrLanguageUnavailableError, OcrPageLimitExceededError,
                    PdfRenderingError, EmptyOcrError, OcrExecutionError, DocumentFileNotFoundError, InvalidPdfError, PdfWithoutTextError,
                    UnsupportedDocumentFormatError, DocumentTooLargeError, EmptyDocumentError) as exc:
                codes = {TesseractUnavailableError: 503, OcrLanguageUnavailableError: 503,
                         OcrPageLimitExceededError: 413, PdfRenderingError: 422,
                         EmptyOcrError: 422, OcrExecutionError: 422, DocumentFileNotFoundError: 404, InvalidPdfError: 400,
                         PdfWithoutTextError: 422, UnsupportedDocumentFormatError: 415,
                         DocumentTooLargeError: 413, EmptyDocumentError: 400}
                raise HTTPException(status_code=codes[type(exc)], detail=str(exc)) from exc
            except CalculationError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except EntityNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
                ) from exc

            except (SelfApprovalNotAllowedError, ApprovalOrderChangeNotAllowedError) as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            except InsufficientApprovalLimitError as exc:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        return handle
