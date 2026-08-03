# Fikak App - Testing Guide

## Overview

This document provides comprehensive instructions for testing the Fikak App with all its integrations including:
- PostgreSQL Database
- JWT Authentication
- File Storage (S3)
- External APIs
- Frontend (Next.js)
- Backend (FastAPI)

---

## Prerequisites

### Required Software
- Docker & Docker Compose (recommended)
- Python 3.11+ (for local backend development)
- Node.js 18+ (for frontend development)
- PostgreSQL 15+ (if not using Docker)
- Git

### Optional
- AWS Account (for S3 testing)
- MinIO (included in Docker Compose for local S3 testing)

---

## Quick Start with Docker (FastAPI stack only)

> These instructions cover the FastAPI/PostgreSQL stack (`docker-compose.yml`). For the unified Frappe stack, use `./setup.sh` and `docker-compose.unified.yml`.

### 1. Environment Setup

```bash
# Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env

# Edit .env files with your configurations
# For local testing, default values work fine
```

### 2. Start All Services

```bash
# Start PostgreSQL, Backend API, and MinIO
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

### 3. Access the Services

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **MinIO Console**: http://localhost:9001
  - Username: value of `MINIO_ROOT_USER` in your `.env`
  - Password: value of `MINIO_ROOT_PASSWORD` in your `.env`

---

## Testing Backend API

### Method 1: Using Makefile

```bash
# Run all backend tests
make backend-test

# Run with coverage report
make test-coverage
```

### Method 2: Manual Testing

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Method 3: Interactive API Testing (Swagger UI)

1. Open http://localhost:8000/docs
2. Test endpoints interactively
3. Click "Try it out" on any endpoint
4. Fill in parameters and execute

---

## Testing Authentication

### 1. Register a New User

**Using cURL:**
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "testpass123"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "email": "test@example.com",
  "username": "testuser",
  "is_active": true,
  "created_at": "2024-01-19T10:30:00"
}
```

### 2. Login and Get Token

**Using cURL:**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass123"
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Access Protected Endpoint

```bash
# Save token from login response
TOKEN="your-access-token-here"

# Get current user info
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Testing Database Integration

### 1. Verify Database Connection

```bash
# Using Docker
docker exec -it fikak_postgres psql -U fikak_user -d fikak_db

# List tables
\dt

# Check users table
SELECT * FROM users;

# Exit
\q
```

### 2. Test CRUD Operations

#### Create a Post
```bash
curl -X POST "http://localhost:8000/api/posts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Post",
    "content": "This is a test post",
    "published": true
  }'
```

#### Get All Posts
```bash
curl -X GET "http://localhost:8000/api/posts?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

#### Update a Post
```bash
curl -X PUT "http://localhost:8000/api/posts/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "published": true
  }'
```

#### Delete a Post
```bash
curl -X DELETE "http://localhost:8000/api/posts/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Testing File Storage (S3)

### Option 1: Using MinIO (Local Testing)

1. **Access MinIO Console**: http://localhost:9001
2. **Login**: use the MinIO credentials from your `.env`
3. **Create Bucket**: Click "Create Bucket" → Name: `fikak-uploads`

4. **Update backend/.env**:
```env
AWS_ACCESS_KEY_ID=<your MINIO_ROOT_USER>
AWS_SECRET_ACCESS_KEY=<your MINIO_ROOT_PASSWORD>
AWS_REGION=us-east-1
S3_BUCKET_NAME=fikak-uploads
S3_ENDPOINT_URL=http://localhost:9000
```

5. **Test File Upload**:
```bash
curl -X POST "http://localhost:8000/api/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your/file.jpg"
```

6. **Get Download URL**:
```bash
curl -X GET "http://localhost:8000/api/files/1/download" \
  -H "Authorization: Bearer $TOKEN"
```

### Option 2: Using AWS S3

1. **Configure AWS Credentials** in `backend/.env`:
```env
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
```

2. **Create S3 Bucket** in AWS Console

3. **Test Upload** (same as above)

---

## Testing External API Integration

### 1. Fetch External Posts

```bash
curl -X GET "http://localhost:8000/api/external/posts?limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "source": "external_api",
  "data": [
    {
      "userId": 1,
      "id": 1,
      "title": "Sample Post",
      "body": "Sample content..."
    }
  ]
}
```

### 2. Fetch External Users

```bash
curl -X GET "http://localhost:8000/api/external/users" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Fetch Single External Post

```bash
curl -X GET "http://localhost:8000/api/external/posts/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Testing Frontend Integration

### 1. Setup Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local

# Start development server
npm run dev
```

### 2. Access Frontend

- Open http://localhost:3000
- You should see the Fikak App home page

### 3. Test User Flows

#### Registration Flow
1. Click "Register"
2. Fill in email, username, password
3. Submit form
4. Should auto-login and redirect to dashboard

#### Login Flow
1. Click "Login"
2. Enter credentials
3. Submit
4. Should redirect to dashboard

#### Posts Management
1. Navigate to "Posts"
2. Click "Create Post"
3. Fill in title and content
4. Submit
5. Verify post appears in list

#### File Upload
1. Navigate to "Files"
2. Click "Choose File"
3. Select a file
4. Upload
5. Verify file appears in list
6. Click "Download" to test retrieval

#### External API
1. Navigate to "External API"
2. View posts from JSONPlaceholder
3. Switch to "Users" tab
4. Verify external data loads

---

## Health Checks

### Backend Health Check

```bash
curl -X GET "http://localhost:8000/health"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "healthy",
  "timestamp": "2024-01-19T10:30:00"
}
```

### Database Health Check

```bash
docker exec -it fikak_postgres pg_isready -U fikak_user -d fikak_db
```

---

## Common Issues and Solutions

### Issue: Database Connection Failed

**Solution:**
```bash
# Check if PostgreSQL is running
docker compose ps

# Restart PostgreSQL
docker compose restart postgres

# Check logs
docker compose logs postgres
```

### Issue: Authentication Token Invalid

**Solution:**
- Token expires after 30 minutes by default
- Re-login to get a new token
- Check SECRET_KEY matches in backend/.env

### Issue: File Upload Fails

**Solution:**
- Verify MinIO is running: `docker compose ps`
- Create bucket in MinIO Console
- Check AWS credentials in backend/.env
- Ensure bucket name is correct

### Issue: CORS Errors

**Solution:**
- Add frontend URL to `CORS_ORIGINS` in backend/.env
- Restart backend service
- Clear browser cache

### Issue: External API Not Working

**Solution:**
- Check internet connection
- Verify `EXTERNAL_API_URL` in backend/.env
- Check API rate limits
- Review backend logs for errors

---

## Performance Testing

### Load Testing with Apache Bench

```bash
# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# Test with authentication
ab -n 100 -c 5 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/posts
```

### Database Query Performance

```sql
-- Check slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## End-to-End Testing Checklist

- [ ] Backend API starts successfully
- [ ] Database connection established
- [ ] User registration works
- [ ] User login works
- [ ] JWT token authentication works
- [ ] Create post operation works
- [ ] Read posts operation works
- [ ] Update post operation works
- [ ] Delete post operation works
- [ ] File upload works (with MinIO or S3)
- [ ] File download URL generation works
- [ ] External API integration works
- [ ] Frontend loads successfully
- [ ] Frontend can communicate with backend
- [ ] All CRUD operations work from frontend
- [ ] File upload works from frontend
- [ ] External API data displays in frontend
- [ ] Health check endpoint returns healthy status
- [ ] Health check returns 503 when the database is stopped
- [ ] Data export (`GET /api/auth/me/export`) returns the user's account, posts, and file metadata
- [ ] Account deletion (`DELETE /api/auth/me`) removes the account, posts, file records, and S3 objects
- [ ] Account deletion returns 503 and retains data when storage cleanup fails (retry succeeds)
- [ ] API documentation is accessible
- [ ] Docker services start and communicate properly

---

## Automated Test Execution

### Run All Tests

```bash
# Using Makefile
make test

# Or manually
cd backend && pytest -v --cov=. --cov-report=term --cov-report=html
```

### Test Coverage Report

After running tests with coverage, open:
```
backend/htmlcov/index.html
```

---

## Cleanup

### Stop Services

```bash
# Stop Docker services
docker compose down

# Stop and remove volumes (WARNING: deletes all data)
docker compose down -v
```

### Reset Database

```bash
make db-reset
```

### Clean Build Artifacts

```bash
make clean
```

---

## Production Testing Notes

### Before Deploying to Production:

1. **Change All Default Secrets**
   - Generate new SECRET_KEY: `openssl rand -hex 32`
   - Update all passwords
   - Use production-grade credentials

2. **Use Production Database**
   - Configure managed PostgreSQL (AWS RDS, etc.)
   - Enable SSL connections
   - Set up backups

3. **Configure Production S3**
   - Use real AWS S3 bucket
   - Set proper IAM policies
   - Enable encryption

4. **Enable Security Features**
   - Set DEBUG=false
   - Configure HTTPS
   - Set secure CORS origins
   - Enable rate limiting

5. **Monitor Performance**
   - Set up logging
   - Configure monitoring (Sentry, etc.)
   - Track metrics
   - Set up alerts

---

## Support

For issues or questions:
- Check backend logs: `docker compose logs backend`
- Check database logs: `docker compose logs postgres`
- Review API docs: http://localhost:8000/docs
- Check TESTING.md for common solutions
