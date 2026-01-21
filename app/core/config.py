"""
Application Configuration
"""
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "qwen3-max"
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # Application Configuration
    APP_NAME: str = "AI Code Analysis Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # File Upload Configuration
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # CORS Configuration
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
