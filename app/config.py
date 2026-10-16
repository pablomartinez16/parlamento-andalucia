import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Parlamento Abierto Andalucía"
    APP_ENV: str = "production"
    DEBUG: bool = False
    
    # Server host & port
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://parlamento_user:parlamento_pass@db:5432/parlamento_db"
    # Fallback/Sync database URL for migrations or SQLite testing
    DATABASE_SYNC_URL: Optional[str] = "postgresql+psycopg2://parlamento_user:parlamento_pass@db:5432/parlamento_db"
    
    # Scraping
    USER_AGENT: str = "ParlamentoAbiertoAndalucia/1.0 (+https://github.com/parlamento-abierto; contacto@parlamento-abierto.es)"
    SCRAPE_RATE_LIMIT_SECONDS: float = 1.0
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    
    # Scheduler
    SYNC_INTERVAL_MINUTES: int = 30
    ENABLE_SCHEDULER: bool = True
    
    # LLM (Pluggable, disabled by default)
    ENABLE_LLM_SUMMARIES: bool = False
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
