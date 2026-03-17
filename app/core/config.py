from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Instagram Dashboard API"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./app/db/dev.db"
    OPENAI_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    STORAGE_BUCKET: str = "instagram-dashboard"
    INSTAGRAM_ACCESS_TOKEN: str = ""
    INSTAGRAM_ACCOUNT_ID: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
