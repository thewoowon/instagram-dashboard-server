from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Instagram Dashboard API"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./app/db/dev.db"
    OPENAI_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    STORAGE_BUCKET: str = "instagram-dashboard"

    # App URL used to build invite acceptance links in emails.
    APP_URL: str = "http://localhost:3000"

    # SMTP (optional — if SMTP_HOST is empty, invite API returns the link without sending mail).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
