from pydantic_settings import BaseSettings
from typing import Optional, List
import os
import logging

logger = logging.getLogger(__name__)


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
    service_port: int = 8001  # Fixed: Made consistent with Dockerfile

    # ATS Analysis Configuration
    ats_analysis_enabled: bool = True
    ats_keyword_cache_ttl: int = 3600  # 1 hour
    ats_score_history_limit: int = 50
    ats_benchmark_update_interval: int = 86400  # 24 hours

    # Performance settings
    max_workers: int = 4
    database_pool_size: int = 10
    database_max_overflow: int = 20

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_configuration()

    def _validate_configuration(self):
        """Validate critical configuration values"""
        try:
            # Validate database URL format
            if not self.database_url.startswith(('postgresql://', 'sqlite://')):
                raise ValueError("DATABASE_URL must be a valid PostgreSQL or SQLite URL")

            # Validate JWT secret key
            if len(self.jwt_secret_key) < 32:
                logger.warning("JWT_SECRET_KEY should be at least 32 characters for security")

            # Validate Redis URL format
            if not self.redis_url.startswith('redis://'):
                raise ValueError("REDIS_URL must be a valid Redis URL")

            # Validate main API URL
            if not self.main_api_url.startswith(('http://', 'https://')):
                raise ValueError("MAIN_API_URL must be a valid HTTP/HTTPS URL")

            # Validate file size limits
            if self.max_file_size > 50 * 1024 * 1024:  # 50MB
                logger.warning("MAX_FILE_SIZE is very large, consider reducing for better performance")

            # Validate service port
            if not (1024 <= self.service_port <= 65535):
                raise ValueError("SERVICE_PORT must be between 1024 and 65535")

            # Create required directories
            os.makedirs(self.pdf_template_path, exist_ok=True)
            os.makedirs(self.static_files_path, exist_ok=True)
            os.makedirs("logs", exist_ok=True)

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise


# Create global settings instance
settings = Settings()