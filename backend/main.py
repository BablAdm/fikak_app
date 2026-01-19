from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import logging

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

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Full-stack API with authentication, database, file storage, and external API integration"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")


# Health check endpoint
@app.get("/health", response_model=schemas.HealthCheck)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow()
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
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get all posts"""
    posts = db.query(models.Post).offset(skip).limit(limit).all()
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

@app.post("/api/files/upload", response_model=schemas.FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Upload a file to S3"""
    try:
        # Generate unique filename
        file_key = f"uploads/{current_user.id}/{datetime.utcnow().timestamp()}_{file.filename}"

        # Upload to S3
        result = s3_storage.upload_file(file.file, file_key)

        # Save to database
        file_upload = models.FileUpload(
            filename=file.filename,
            file_key=file_key,
            file_size=file.size,
            content_type=file.content_type,
            bucket_name=result["bucket"],
            user_id=current_user.id
        )
        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)

        return file_upload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/files/{file_id}/download")
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
        raise HTTPException(status_code=500, detail=str(e))


# ==================== External API Endpoints ====================

@app.get("/api/external/posts")
async def get_external_posts(
    limit: Optional[int] = 10,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Fetch posts from external API"""
    try:
        posts = await external_api_client.get_posts(limit)
        return {"source": "external_api", "data": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/external/posts/{post_id}")
async def get_external_post(
    post_id: int,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Fetch a single post from external API"""
    try:
        post = await external_api_client.get_post_by_id(post_id)
        return {"source": "external_api", "data": post}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/external/users")
async def get_external_users(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Fetch users from external API"""
    try:
        users = await external_api_client.get_users()
        return {"source": "external_api", "data": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
