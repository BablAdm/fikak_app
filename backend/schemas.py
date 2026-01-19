from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, List


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


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
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# File Upload Schemas
class FileUploadResponse(BaseModel):
    id: int
    filename: str
    file_key: str
    file_size: int
    content_type: str
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
