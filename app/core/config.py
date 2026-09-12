from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    app_name: str = "InsightPilot AI"
    app_version: str = "2.0.0"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "insightpilot_db"
    db_user: str = "insightpilot_readonly"
    db_password: str

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.7-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
