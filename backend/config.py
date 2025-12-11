"""
Configuration management for Knowledge Distillery
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str = "postgresql+asyncpg://kd_user:kd_password@db:5432/knowledge_distillery"
    
    # SMTP Email Configuration
    smtp_host: str = "mail.khtain.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "Knowledge Distillery"
    
    # Email Recipients (comma-separated string)
    email_recipients: str = ""
    
    # OpenRouter AI Configuration
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    
    # Upload Configuration
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10
    
    @property
    def recipient_list(self) -> List[str]:
        """Parse comma-separated recipients into a list"""
        if not self.email_recipients:
            return []
        return [email.strip() for email in self.email_recipients.split(",") if email.strip()]
    
    @property
    def ai_configured(self) -> bool:
        """Check if AI is properly configured"""
        return bool(self.openrouter_api_key and self.openrouter_api_key != "your-openrouter-api-key-here")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()

