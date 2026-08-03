from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging
import secrets

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings and configuration"""

    # Application
    app_name: str = "Fikak App API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database (set DATABASE_URL in .env; default has no embedded credentials)
    database_url: str = "postgresql://fikak_user@localhost:5432/fikak_db"

    # JWT Authentication (set SECRET_KEY in the environment for production;
    # an empty value triggers an ephemeral per-process key, see get_settings)
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # AWS S3 / File Storage
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "fikak-uploads"
    # Custom S3 endpoint for S3-compatible storage (e.g. MinIO:
    # http://localhost:9000); leave empty for AWS S3
    s3_endpoint_url: str = ""

    # External API (example)
    external_api_url: str = "https://jsonplaceholder.typicode.com"
    external_api_key: str = ""

    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings():
    """Return the cached application settings.

    If SECRET_KEY is not provided, generate an ephemeral per-process key so
    development still works, and warn loudly: tokens signed with it will not
    survive restarts or be valid across multiple workers.
    """
    settings = Settings()
    if not settings.secret_key:
        settings.secret_key = secrets.token_urlsafe(32)
        logger.warning(
            "SECRET_KEY is not set - generated an ephemeral key. JWTs will be "
            "invalidated on restart and will not work across multiple workers. "
            "Set SECRET_KEY in the environment for production."
        )
    return settings
