from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "RailConnect"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./railconnect.db"
    
    # JWT & Auth
    SECRET_KEY: str = "railconnect-super-secret-key-change-in-production-198273"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    RESET_TOKEN_EXPIRE_MINUTES: int = 15
    
    # Initial Admin Seed
    INITIAL_ADMIN_EMAIL: str = "admin@railconnect.com"
    INITIAL_ADMIN_PASSWORD: str = "Admin@ChangeMe123"
    INITIAL_ADMIN_NAME: str = "Railway Super Admin"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
