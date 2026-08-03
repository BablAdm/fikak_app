# Fikak App - Complete Setup Guide

This guide will walk you through setting up the Fikak App for testing and development.

---

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Backend Setup](#backend-setup)
3. [Frontend Setup](#frontend-setup)
4. [Database Configuration](#database-configuration)
5. [File Storage Setup](#file-storage-setup)
6. [Running the Application](#running-the-application)
7. [Testing as End User](#testing-as-end-user)

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd fikak_app
```

### 2. Install Docker (if not installed)

**macOS:**
```bash
brew install --cask docker
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

**Windows:**
Download from https://www.docker.com/products/docker-desktop

### 3. Verify Docker Installation

```bash
docker --version
docker-compose --version
```

---

## Backend Setup (FastAPI stack only)

> These instructions cover the FastAPI/PostgreSQL stack. For the unified Frappe stack, use `./setup.sh` and `docker-compose.unified.yml` instead.

### Option 1: Using Docker (Recommended)

```bash
# 1. Copy environment file
cp backend/.env.example backend/.env

# 2. (Optional) Edit backend/.env if needed
# Default values work for local testing

# 3. Start services with Docker Compose
docker-compose up -d

# 4. Verify backend is running
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "database": "healthy",
  "timestamp": "2024-01-19T10:30:00"
}
```

### Option 2: Local Development (Without Docker)

```bash
# 1. Install Python 3.11+
python --version  # Verify installation

# 2. Create virtual environment
cd backend
python -m venv venv

# 3. Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set up PostgreSQL
# Install PostgreSQL locally or use Docker:
docker run --name fikak_postgres \
  -e POSTGRES_USER=fikak_user \
  -e POSTGRES_PASSWORD=<your-db-password> \
  -e POSTGRES_DB=fikak_db \
  -p 5432:5432 \
  -d postgres:15-alpine

# 6. Copy and configure environment
cp .env.example .env
# Edit .env with your database URL

# 7. Start the backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Verify Backend Installation

1. Open browser to http://localhost:8000
2. You should see: `{"message": "Welcome to Fikak App API", ...}`
3. Open http://localhost:8000/docs for API documentation

---

## Frontend Setup

### If Using Your Own Frontend Repo

```bash
# 1. Clone your frontend repository into the project
git clone <your-frontend-repo-url> frontend

# 2. Navigate to frontend
cd frontend

# 3. Install dependencies
npm install
# or
yarn install

# 4. Configure environment
# Create .env.local file with:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 5. Start development server
npm run dev
# or
yarn dev

# 6. Open browser to http://localhost:3000
```

### If Using Provided Frontend Template

```bash
# Follow the same steps as above
# The frontend template is already configured
cd frontend
npm install
npm run dev
```

---

## Database Configuration

### Using Docker Compose (Automatic)

Docker Compose automatically sets up PostgreSQL. No manual configuration needed!

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Connect to database
docker exec -it fikak_postgres psql -U fikak_user -d fikak_db

# List tables
\dt

# Exit
\q
```

### Using Local PostgreSQL

```bash
# 1. Install PostgreSQL
brew install postgresql@15  # macOS
sudo apt install postgresql-15  # Ubuntu

# 2. Start PostgreSQL service
brew services start postgresql@15  # macOS
sudo systemctl start postgresql  # Ubuntu

# 3. Create database and user
psql postgres
CREATE USER fikak_user WITH PASSWORD '<your-db-password>';
CREATE DATABASE fikak_db OWNER fikak_user;
\q

# 4. Update backend/.env
DATABASE_URL=postgresql://fikak_user:<your-db-password>@localhost:5432/fikak_db
```

### Database Migration (First Time)

The application automatically creates tables on first run. To verify:

```bash
# Using Docker
docker exec -it fikak_postgres psql -U fikak_user -d fikak_db -c "\dt"

# Expected tables:
# users
# posts
# file_uploads
# external_api_cache
```

---

## File Storage Setup

### Option 1: MinIO (Local S3 - Recommended for Testing)

MinIO is included in Docker Compose and provides S3-compatible storage locally.

```bash
# 1. Start MinIO
docker-compose up -d minio

# 2. Access MinIO Console
# Open http://localhost:9001
# Login with the MINIO_ROOT_USER / MINIO_ROOT_PASSWORD values from your .env

# 3. Create Bucket
# - Click "Create Bucket"
# - Name: fikak-uploads
# - Click "Create Bucket"

# 4. Configure Backend
# Edit backend/.env:
AWS_ACCESS_KEY_ID=<your MINIO_ROOT_USER>
AWS_SECRET_ACCESS_KEY=<your MINIO_ROOT_PASSWORD>
AWS_REGION=us-east-1
S3_BUCKET_NAME=fikak-uploads
S3_ENDPOINT_URL=http://localhost:9000

# 5. Restart backend
docker-compose restart backend
```

### Option 2: AWS S3 (Production)

```bash
# 1. Create S3 Bucket in AWS Console
# - Go to S3 service
# - Click "Create bucket"
# - Name: your-unique-bucket-name
# - Region: us-east-1 (or your preferred region)
# - Keep default settings
# - Click "Create bucket"

# 2. Create IAM User with S3 Access
# - Go to IAM service
# - Create user with programmatic access
# - Attach a bucket-scoped custom policy (do NOT use AmazonS3FullAccess).
#   Grant only s3:PutObject, s3:GetObject, s3:DeleteObject on
#   arn:aws:s3:::<your-bucket-name>/uploads/* and s3:ListBucket on
#   arn:aws:s3:::<your-bucket-name>
#   (replace <your-bucket-name> with the bucket you created in step 1;
#   it must also match S3_BUCKET_NAME in backend/.env)
# - Save Access Key ID and Secret Access Key

# 3. Configure Backend
# Edit backend/.env:
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# 4. Restart backend
docker-compose restart backend
```

### Option 3: Skip File Storage (Optional)

File upload features will not work, but everything else will function normally.

```bash
# Leave AWS credentials empty in backend/.env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

---

## Running the Application

### Complete Stack with Docker

```bash
# 1. Start all services
docker-compose up -d

# 2. Check status
docker-compose ps

# Expected output:
# fikak_postgres   Up (healthy)
# fikak_backend    Up
# fikak_minio      Up (healthy)

# 3. View logs
docker-compose logs -f

# 4. Start frontend (in new terminal)
cd frontend
npm run dev
```

### Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001
- **PostgreSQL**: localhost:5432

---

## Testing as End User

### 1. Register a New Account

1. Open http://localhost:3000
2. Click "Register" button
3. Fill in registration form:
   - Email: `tester@example.com`
   - Username: `tester`
   - Password: `Test123!`
4. Click "Register"
5. You should be automatically logged in

### 2. Test Dashboard

After login, you should see:
- Welcome message with your username
- Account information
- Quick links to features

### 3. Test Posts Feature

1. Click "Posts" in navigation
2. Click "Create Post" button
3. Fill in the form:
   - Title: "My First Post"
   - Content: "This is a test post"
   - Check "Publish immediately"
4. Click "Create Post"
5. Verify post appears in list
6. Try editing and deleting posts

### 4. Test File Upload

1. Click "Files" in navigation
2. Click "Choose File"
3. Select any image or document
4. File should upload and appear in list
5. Click "Download" to verify retrieval

**Note**: Requires MinIO or AWS S3 setup (see File Storage Setup)

### 5. Test External API Integration

1. Click "External API" in navigation
2. View posts fetched from JSONPlaceholder API
3. Click "Users" tab
4. View user data from external source
5. Verify data loads correctly

### 6. Test Authentication Flow

1. Click "Logout"
2. Verify redirect to home page
3. Click "Login"
4. Enter credentials
5. Verify successful login

---

## API Testing (for Developers)

### Using Swagger UI

1. Open http://localhost:8000/docs
2. Click on any endpoint to expand
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"

### Using cURL

```bash
# Register user
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dev@example.com",
    "username": "developer",
    "password": "DevPass123"
  }'

# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=developer&password=DevPass123"

# Save the token from response
TOKEN="your-token-here"

# Create post
curl -X POST "http://localhost:8000/api/posts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Test Post",
    "content": "Created via cURL",
    "published": true
  }'

# Get all posts
curl -X GET "http://localhost:8000/api/posts" \
  -H "Authorization: Bearer $TOKEN"
```

### Using Postman

1. Import the API documentation from http://localhost:8000/openapi.json
2. Create an environment with:
   - `base_url`: http://localhost:8000
   - `token`: (will be set after login)
3. Test endpoints

---

## Verification Checklist

Use this checklist to ensure everything is working:

### Backend
- [ ] Backend starts without errors
- [ ] Health endpoint returns healthy status
- [ ] API documentation is accessible at `/docs`
- [ ] Database connection is established
- [ ] Can register a new user
- [ ] Can login and receive JWT token
- [ ] Protected endpoints require authentication
- [ ] Can create, read, update, delete posts
- [ ] External API endpoints return data

### Frontend
- [ ] Frontend loads successfully
- [ ] Can access home page
- [ ] Registration form works
- [ ] Login form works
- [ ] Dashboard displays after login
- [ ] Can navigate between pages
- [ ] Posts page shows and manages posts
- [ ] Files page allows upload (if storage configured)
- [ ] External API page displays data
- [ ] Logout works correctly

### Integrations
- [ ] Database stores user data
- [ ] JWT tokens work for authentication
- [ ] File uploads work (if S3/MinIO configured)
- [ ] External API proxy works
- [ ] All CRUD operations persist to database
- [ ] Frontend communicates with backend successfully

---

## Stopping the Application

```bash
# Stop Docker services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Stop frontend (Ctrl+C in terminal where it's running)
```

---

## Next Steps

1. Review [TESTING.md](./TESTING.md) for comprehensive testing guide
2. Read [README.md](./README.md) for API documentation
3. Customize the application for your needs
4. Deploy to production (see README.md deployment section)

---

## Getting Help

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Review [TESTING.md](./TESTING.md) troubleshooting section
3. Verify all environment variables are set correctly
4. Ensure all required services are running
5. Check that ports 3000, 8000, 5432, 9000, 9001 are available

---

## Summary

You've now set up:
- ✅ FastAPI backend with authentication
- ✅ PostgreSQL database
- ✅ S3-compatible file storage (MinIO or AWS)
- ✅ External API integration
- ✅ Next.js frontend (if applicable)
- ✅ Complete testing environment

The application is ready for testing and development!
