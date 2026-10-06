import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name: str = "BB Contas IA"
    database_url: str = os.getenv("DATABASE_URL", "")


settings = Settings()
