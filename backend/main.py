from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_, literal, select
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging
import os
import re
import uuid

from config import get_settings
from database import get_db, init_db
import models
import schemas
import auth
from storage import s3_storage
from external_api import external_api_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database when the application starts"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
    yield


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Full-stack API with authentication, database, file storage, and external API integration",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB
# Slack for multipart boundaries/headers when comparing Content-Length
UPLOAD_SIZE_SLACK = 1024 * 1024

INTERNAL_ERROR_DETAIL = "Internal server error"
INTERNAL_ERROR_RESPONSES = {500: {"description": INTERNAL_ERROR_DETAIL}}


@app.middleware("http")
async def reject_oversized_uploads(request: Request, call_next):
    """Reject oversized upload requests before the body is buffered.

    Nginx also caps request bodies (client_max_body_size), but direct
    backend deployments bypass the proxy, so enforce it here too.
    """
    if request.url.path == "/api/files/upload" and request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length is None:
            # Chunked uploads would bypass the size check below and be fully
            # buffered by the multipart parser before the route could reject
            # them, so require a declared length up front
            return JSONResponse(
                status_code=status.HTTP_411_LENGTH_REQUIRED,
                content={"detail": "Content-Length header is required for uploads"},
            )
        try:
            declared_length = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid Content-Length header"},
            )
        if declared_length > MAX_UPLOAD_SIZE + UPLOAD_SIZE_SLACK:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": f"File exceeds maximum size of {MAX_UPLOAD_SIZE // (1024 * 1024)} MB"},
            )
    return await call_next(request)


# Health check endpoint
@app.get("/health", response_model=schemas.HealthCheck)
def health_check(response: Response, db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection using parameterized query (not raw SQL)
        db.scalar(select(literal(1)))
        db_status = "healthy"
        overall_status = "healthy"
    except Exception:
        # Log the error for debugging, but don't expose details to clients
        logger.exception("Database health check failed")
        db_status = "unhealthy"
        overall_status = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc)
    }


# ==================== Authentication Endpoints ====================

@app.post("/api/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()

    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )

    # Create new user
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.post("/api/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    user = auth.authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_current_user_info(current_user: models.User = Depends(auth.get_current_active_user)):
    """Get current user information"""
    return current_user


@app.get("/api/auth/me/export")
def export_my_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Export all personal data held for the current user (GDPR/CCPA data portability)"""
    posts = db.query(models.Post).filter(models.Post.user_id == current_user.id).all()
    files = db.query(models.FileUpload).filter(models.FileUpload.user_id == current_user.id).all()

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "created_at": current_user.created_at,
        },
        "posts": [
            {"id": p.id, "title": p.title, "content": p.content,
             "published": p.published, "created_at": p.created_at}
            for p in posts
        ],
        "files": [
            {"id": f.id, "filename": f.filename, "file_size": f.file_size,
             "content_type": f.content_type, "created_at": f.created_at}
            for f in files
        ],
    }


@app.delete("/api/auth/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Delete the current user's account and all associated data (GDPR/CCPA right to erasure).

    See PRIVACY.md for the data inventory and erasure policy. Deletion is
    synchronous and aborts (so the user can retry) if any stored object
    cannot be removed; an audit record is logged on completion.
    """
    files = db.query(models.FileUpload).filter(models.FileUpload.user_id == current_user.id).all()
    for file_upload in files:
        try:
            deleted = s3_storage.delete_file(file_upload.file_key, file_upload.bucket_name)
        except Exception as e:
            # Log the internal record id only - the storage key embeds a
            # user-supplied filename and may contain personal data
            logger.warning(f"Could not delete S3 object for file id={file_upload.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not delete all account data; please retry"
            ) from e
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not delete all account data; please retry"
            )
        db.delete(file_upload)

    posts_deleted = db.query(models.Post).filter(models.Post.user_id == current_user.id).delete()
    user_id = current_user.id
    db.delete(current_user)
    db.commit()
    # Audit record for the erasure request (no PII beyond the internal id)
    logger.info(
        f"Erasure completed for user id={user_id}: "
        f"{len(files)} file(s), {posts_deleted} post(s), account removed"
    )
    return None


# ==================== Post Endpoints ====================

@app.post("/api/posts", response_model=schemas.PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Create a new post"""
    new_post = models.Post(**post.model_dump(), user_id=current_user.id)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@app.get("/api/posts", response_model=List[schemas.PostResponse])
def get_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get all published posts plus the current user's own drafts"""
    posts = (
        db.query(models.Post)
        .filter(or_(models.Post.published.is_(True), models.Post.user_id == current_user.id))
        .order_by(models.Post.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return posts


@app.get("/api/posts/{post_id}", response_model=schemas.PostResponse)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get a specific post"""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not post.published and post.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.put("/api/posts/{post_id}", response_model=schemas.PostResponse)
def update_post(
    post_id: int,
    post_update: schemas.PostUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Update a post"""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check ownership
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")

    # Update fields
    for key, value in post_update.model_dump(exclude_unset=True).items():
        setattr(post, key, value)

    db.commit()
    db.refresh(post)
    return post


@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Delete a post"""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check ownership
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    db.delete(post)
    db.commit()
    return None


# ==================== File Upload Endpoints ====================

@app.post("/api/files/upload", response_model=schemas.FileUploadResponse, responses=INTERNAL_ERROR_RESPONSES)
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Upload a file to S3 (sync route: boto3 I/O runs in the threadpool)"""
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_SIZE // (1024 * 1024)} MB"
        )

    # Sanitize the user-supplied filename before it becomes part of the
    # storage key: strip any path components and disallowed characters
    safe_filename = os.path.basename(file.filename or "")
    safe_filename = re.sub(r"[^A-Za-z0-9._-]", "_", safe_filename)[:255] or "upload"

    # Generate a unique, collision-free storage key
    file_key = f"uploads/{current_user.id}/{uuid.uuid4().hex}_{safe_filename}"

    try:
        # Upload to S3
        result = s3_storage.upload_file(file.file, file_key)
    except Exception as e:
        logger.exception("File upload to storage failed")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL) from e

    try:
        # Save to database
        file_upload = models.FileUpload(
            filename=safe_filename,
            file_key=file_key,
            file_size=file_size,
            content_type=file.content_type,
            bucket_name=result["bucket"],
            user_id=current_user.id
        )
        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)
        return file_upload
    except Exception as e:
        # Metadata persistence failed: remove the just-uploaded object so
        # no untracked storage is left behind
        logger.exception("Persisting file metadata failed; removing uploaded object")
        try:
            s3_storage.delete_file(file_key, result["bucket"])
        except Exception:
            logger.exception("Cleanup of uploaded object failed")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL) from e


@app.get("/api/files", response_model=List[schemas.FileUploadResponse])
def get_user_files(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get all files uploaded by current user"""
    files = db.query(models.FileUpload).filter(
        models.FileUpload.user_id == current_user.id
    ).all()
    return files


@app.get("/api/files/{file_id}/download", responses=INTERNAL_ERROR_RESPONSES)
def get_file_download_url(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get presigned URL for file download"""
    file_upload = db.query(models.FileUpload).filter(models.FileUpload.id == file_id).first()

    if not file_upload:
        raise HTTPException(status_code=404, detail="File not found")

    if file_upload.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")

    try:
        download_url = s3_storage.get_presigned_url(file_upload.file_key, file_upload.bucket_name)
        return {"download_url": download_url, "expires_in": 3600}
    except Exception as e:
        logger.exception("Failed to generate download URL")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL) from e


# ==================== External API Endpoints ====================

@app.get("/api/external/posts", responses=INTERNAL_ERROR_RESPONSES)
async def get_external_posts(
    limit: int = Query(10, ge=1, le=100),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Fetch posts from external API"""
    try:
        posts = await external_api_client.get_posts(limit)
        return {"source": "external_api", "data": posts}
    except Exception as e:
        logger.exception("Failed to fetch external posts")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL) from e


@app.get("/api/external/posts/{post_id}", responses=INTERNAL_ERROR_RESPONSES)
async def get_external_post(
    post_id: int,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Fetch a single post from external API"""
    try:
        post = await external_api_client.get_post_by_id(post_id)
        return {"source": "external_api", "data": post}
    except Exception as e:
        logger.exception("Failed to fetch external post")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL) from e


@app.get("/api/external/users", responses=INTERNAL_ERROR_RESPONSES)
async def get_external_users(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Fetch users from external API"""
    try:
        users = await external_api_client.get_users()
        return {"source": "external_api", "data": users}
    except Exception as e:
        logger.exception("Failed to fetch external users")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL) from e


# Root endpoint
@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Welcome to Fikak App API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
