from fastapi import HTTPException, status
from fastapi.routing import APIRoute

from app.services.exceptions import EntityNotFoundError


class EntityNotFoundRoute(APIRoute):
    """Traduz erros de entidades ausentes exclusivamente na camada HTTP."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request):
            try:
                return await handler(request)
            except EntityNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
                ) from exc

        return handle
