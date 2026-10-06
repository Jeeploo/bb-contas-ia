import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name: str = "BB Contas IA"
    document_storage_path: str = os.getenv("DOCUMENT_STORAGE_PATH", "./storage/documentos")
    document_max_size_bytes: int = int(os.getenv("DOCUMENT_MAX_SIZE_BYTES", "10485760"))
    database_url: str = os.getenv("DATABASE_URL", "")


settings = Settings()
