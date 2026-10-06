from fastapi import HTTPException, status
from fastapi.routing import APIRoute

from app.services.exceptions import (
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
            except EntityNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
                ) from exc

            except (SelfApprovalNotAllowedError, ApprovalOrderChangeNotAllowedError) as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            except InsufficientApprovalLimitError as exc:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        return handle
