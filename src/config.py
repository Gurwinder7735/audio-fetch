from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    download_dir: Path = Path("downloads")
    max_concurrent_downloads: int = 5
    retry_count: int = 3

    @property
    def downloads_path(self) -> Path:
        path = self.download_dir.resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
