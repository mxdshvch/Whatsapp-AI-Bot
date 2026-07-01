from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./chatbot.db"

    # OpenRouter API
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-2-70b-chat"

    # Wappi API
    wappi_token: str = ""
    wappi_instance_id: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Admin
    admin_username: str = "admin"
    admin_password: str = "change-me"

    # Security
    secret_key: str = "change-me-in-production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Scheduler settings
    message_interval_minutes: int = 40
    work_start_hour: int = 9
    work_end_hour: int = 19
    timezone: str = "Europe/Moscow"

    class Config:
        env_file = ".env"


settings = Settings()
