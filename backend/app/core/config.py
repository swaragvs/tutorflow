"""Configuration module using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings read from environment variables."""

    # Database
    DATABASE_URL: str

    # JWT / Auth
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 1440  # default 24h

    # Gemini AI
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
