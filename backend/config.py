from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings and configuration"""

    # Application
    app_name: str = "Fikak App API"
    app_version: str = "1.0.0"
    debug: bool = True

    # Database
    database_url: str = "postgresql://fikak_user:fikak_pass@localhost:5432/fikak_db"

    # JWT Authentication
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # AWS S3 / File Storage
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "fikak-uploads"

    # External API (example)
    external_api_url: str = "https://jsonplaceholder.typicode.com"
    external_api_key: str = ""

    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
