"""
Application Configuration
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DB_URL: str = os.getenv("DATABASE_URL")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "NRTaxAI"
    
    # Security
    SECRET_KEY: str = "nr12ta56x89y7"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120 # 2 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256" # HS256 is the default algorithm for JWT
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # Database
    DATABASE_URL: str = DB_URL
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # S3
    S3_BUCKET_UPLOADS: str = "nrtaxai-uploads" # Tax form document uploads (W2, 1099-INT, 1099-NEC, 1098-T, 1042-S, 1099-DIV, 1099-B, 1099-MISC)
    S3_BUCKET_PDFS: str = "nrtaxai-pdfs" # Tax forms generated PDFs (1040-NR, 1040-V, 8843, W-8BEN, 8879(e-file))
    S3_BUCKET_EXTRACTS: str = "nrtaxai-extracts"
    
    # KMS
    KMS_KEY_ID: str = "arn:aws:kms:us-east-1:123456789012:key/your-kms-key-id"
    
    # Textract
    TEXTRACT_ROLE_ARN: str = "arn:aws:iam::123456789012:role/TextractRole"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = OPENAI_API_KEY
    
    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # File upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "png", "jpg", "jpeg"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
