from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.core.database import test_database_connection


app = FastAPI(
    title=settings.app_name,
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "API BB Contas IA funcionando"
    }


@app.get("/health")
def health():
    db_status = test_database_connection()

    return {
        "status": "ok",
        "database": "connected" if db_status == 1 else "error",
    }
