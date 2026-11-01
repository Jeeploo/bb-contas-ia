import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    document_ai_provider: str = os.getenv("DOCUMENT_AI_PROVIDER", "openai").strip().lower()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_document_model: str = os.getenv("GEMINI_DOCUMENT_MODEL", "gemini-2.5-flash-lite").strip()
    gemini_document_timeout: float = float(os.getenv("GEMINI_DOCUMENT_TIMEOUT", "90"))
    gemini_document_max_output_tokens: int = int(os.getenv("GEMINI_DOCUMENT_MAX_OUTPUT_TOKENS", "6000"))
    uf_mvp: str = os.getenv("UF_MVP", "PE").strip().upper()
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_document_model: str = os.getenv("OPENAI_DOCUMENT_MODEL", "").strip()
    openai_document_timeout: float = float(os.getenv("OPENAI_DOCUMENT_TIMEOUT", "90"))
    openai_document_max_output_tokens: int = int(os.getenv("OPENAI_DOCUMENT_MAX_OUTPUT_TOKENS", "6000"))
    app_name: str = "BB Contas IA"
    document_storage_path: str = os.getenv("DOCUMENT_STORAGE_PATH", "./storage/documentos")
    document_max_size_bytes: int = int(os.getenv("DOCUMENT_MAX_SIZE_BYTES", "10485760"))
    max_ocr_pages: int = int(os.getenv("MAX_OCR_PAGES", "10"))
    database_url: str = os.getenv("DATABASE_URL", "")


settings = Settings()
