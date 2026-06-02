from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    llm_provider: str = "ollama"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    database_url: str = ""
    mongodb_url: str = ""
    mongodb_db: str = "asim"
    redis_url: str = "redis://localhost:6379"
    app_env: str = "development"
    fastapi_port: int = 8000
    secret_key: str = ""
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    internal_api_secret: str = ""


settings = Settings()
