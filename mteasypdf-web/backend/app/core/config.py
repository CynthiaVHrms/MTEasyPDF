from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MTEasyPDF Web"
    storage_dir: Path = Path("C:/mteasypdf_jobs")
    max_upload_size_mb: int = 1024
    retention_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
settings.storage_dir = settings.storage_dir.resolve()
settings.storage_dir.mkdir(parents=True, exist_ok=True)