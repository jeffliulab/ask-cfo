"""
Tax Service 配置管理
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "WENCFO Tax Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # 数据库配置
    DATABASE_URL: str
    
    # Redis配置
    REDIS_URL: str
    
    # S3配置
    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str
    S3_REGION: str = "us-east-1"
    
    # AI配置
    OPENAI_API_KEY: str
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: Optional[str] = None
    
    # 后端服务配置
    BACKEND_URL: str = "http://backend:8000"
    BRAIN_URL: str = "http://brain:8001"
    
    # 报税配置
    TAX_SERVICE_MODE: str = "auto"  # auto, manual, hybrid
    TAX_API_ENABLED: bool = True
    TAX_BROWSER_AUTOMATION_ENABLED: bool = True
    
    # API报税配置
    TAX_API_TIMEOUT: int = 30
    TAX_API_RETRY_COUNT: int = 3
    
    # 浏览器自动化配置
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 60
    BROWSER_WAIT_TIMEOUT: int = 10
    
    # 定时任务配置
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # 安全配置
    CORS_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"


settings = Settings()
