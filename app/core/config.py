from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    # Database
    database_url: str
    test_database_url: Optional[str] = None

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # External APIs
    main_api_url: str
    main_api_timeout: int = 10

    # PDF Generation
    pdf_template_path: str = "./templates/pdf/"
    static_files_path: str = "./static/"

    # Environment
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # File Upload
    max_file_size: int = 10485760  # 10MB
    allowed_file_types: List[str] = ["pdf", "doc", "docx"]

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Service Configuration
    service_name: str = "resume-builder-service"
    service_version: str = "1.0.0"
    service_port: int = 8002

    # ATS Analysis Configuration
    ats_analysis_enabled: bool = True
    ats_keyword_cache_ttl: int = 3600  # 1 hour
    ats_score_history_limit: int = 50
    ats_benchmark_update_interval: int = 86400  # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()