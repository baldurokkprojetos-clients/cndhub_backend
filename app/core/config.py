from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Hub CND Politeto API"
    VERSION: str = "1.0.0"
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Worker Settings
    API_BASE_URL: str = "http://localhost:8000"

    FRONTEND_URL: str = "http://localhost:3000"
    
    # Supabase Settings (for file upload)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_BUCKET: str = "certidoes"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
