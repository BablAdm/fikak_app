from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, List


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Enforce minimum password length and reject passwords longer than bcrypt's 72-byte limit"""
        password_bytes = v.encode("utf-8")
        if len(password_bytes) < 8:
            raise ValueError("Password must be at least 8 bytes long")
        if len(password_bytes) > 72:
            raise ValueError("Password must not exceed 72 bytes")
        return v


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: str
    password: str


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Post Schemas
class PostBase(BaseModel):
    title: str
    content: str
    published: bool = False


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    published: Optional[bool] = None


class PostResponse(PostBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# File Upload Schemas
class FileUploadResponse(BaseModel):
    id: int
    filename: str
    file_key: str
    file_size: int
    # Nullable to match the model: multipart parts may omit Content-Type
    content_type: Optional[str] = None
    bucket_name: str
    created_at: datetime
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# External API Schemas
class ExternalDataResponse(BaseModel):
    userId: int
    id: int
    title: str
    body: str


# Health Check
class HealthCheck(BaseModel):
    status: str
    database: str
    timestamp: datetime
