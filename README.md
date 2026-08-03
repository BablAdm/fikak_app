# Fikak App

A complete full-stack financial services application with eligibility assessment, KYC workflows, banking integrations, and multi-language support.

## 🚀 Complete Integration Setup (New!)

This repository now includes a **complete integration** of all Fikak App components:

- ✅ **fikak-ui**: Next.js 14 frontend with React 18 (EN/AR/FR languages)
- ✅ **Frappe Framework**: Python ERP backend with custom fikak_app
- ✅ **Full Infrastructure**: Docker Compose orchestration for production-ready deployment

### Quick Start (3 Commands)

```bash
# 1. Run automated setup
./setup.sh

# 2. Install custom Frappe app
./install-fikak-app.sh

# 3. Open browser → http://localhost
# Login: Administrator / admin
```

### Documentation

- 📖 **[USER_TESTING_GUIDE.md](USER_TESTING_GUIDE.md)** - For end-user testing (start here!)
- 🛠️ **[COMPLETE_SETUP.md](COMPLETE_SETUP.md)** - Complete deployment guide
- 🧪 **[TESTING.md](TESTING.md)** - Detailed API testing instructions

### What's Included

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Next.js 14 + React 18 | User interface with multi-language |
| Backend | Frappe Framework v15 | ERP system with custom APIs |
| Database | MariaDB 10.6 | Persistent data storage |
| Cache | Redis 6.2 | Session and queue management |
| Proxy | Nginx | Reverse proxy and routing |
| Workers | RQ | Background job processing |

### Access Points

- **Main App**: http://localhost
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/method
- **Frappe Desk**: http://localhost:8000/app

---

## Features (Original FastAPI Backend - Available)

### Backend (FastAPI)
- **JWT Authentication** - Secure user registration and login with JWT tokens
- **PostgreSQL Database** - Full CRUD operations with SQLAlchemy ORM
- **File Storage** - S3-compatible file upload/download (AWS S3 or MinIO)
- **External API Integration** - Proxy and cache external API calls
- **Auto-generated API Docs** - Interactive Swagger UI at `/docs`
- **Health Monitoring** - Built-in health check endpoints
- **Comprehensive Testing** - Unit and integration tests with pytest

### Frontend (Next.js)
- **React 18** with TypeScript
- **Server-Side Rendering** (SSR) and Static Generation
- **State Management** with Zustand
- **API Integration** with Axios
- **Responsive Design** - Mobile-friendly UI

### Infrastructure
- **Docker Compose** - One-command setup for all services
- **PostgreSQL 15** - Reliable, production-ready database
- **MinIO** - S3-compatible storage for local development
- **Automated Testing** - CI/CD ready test suite

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- (Optional) Node.js 18+ and Python 3.11+ for local development

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd fikak_app

# Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env

# (Optional) Customize .env files for your setup
```

### 2. Start with Docker (Recommended)

```bash
# Start all services (PostgreSQL, Backend API, MinIO)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Access the Application

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (credentials from MINIO_ROOT_USER / MINIO_ROOT_PASSWORD in your .env)
- **PostgreSQL**: localhost:5432

### 4. Create Your First User

Using the interactive API docs at http://localhost:8000/docs:

1. Go to `/api/auth/register` endpoint
2. Click "Try it out"
3. Enter user details:
   ```json
   {
     "email": "user@example.com",
     "username": "testuser",
     "password": "securepass123"
   }
   ```
4. Execute
5. Copy the returned user ID

### 5. Login and Get Token

1. Go to `/api/auth/login` endpoint
2. Enter credentials
3. Copy the `access_token` from response
4. Click "Authorize" button at top
5. Enter: `Bearer <your-token>`
6. Now you can access all protected endpoints!

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Compose                      │
├─────────────────┬─────────────────┬────────────────────┤
│   PostgreSQL    │   Backend API   │      MinIO         │
│   (Database)    │    (FastAPI)    │  (File Storage)    │
│   Port: 5432    │   Port: 8000    │  Port: 9000/9001   │
└─────────────────┴─────────────────┴────────────────────┘
         │                 │                  │
         └─────────────────┴──────────────────┘
                           │
                    ┌──────┴──────┐
                    │   Frontend  │
                    │  (Next.js)  │
                    │ Port: 3000  │
                    └─────────────┘
```

---

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info (protected)

### Posts (Protected)
- `GET /api/posts` - Get all posts
- `GET /api/posts/{id}` - Get specific post
- `POST /api/posts` - Create new post
- `PUT /api/posts/{id}` - Update post
- `DELETE /api/posts/{id}` - Delete post

### File Management (Protected)
- `POST /api/files/upload` - Upload file to S3
- `GET /api/files` - Get user's uploaded files
- `GET /api/files/{id}/download` - Get presigned download URL

### External API (Protected)
- `GET /api/external/posts` - Fetch posts from external API
- `GET /api/external/posts/{id}` - Fetch single post
- `GET /api/external/users` - Fetch users from external API

### System
- `GET /` - API info
- `GET /health` - Health check
- `GET /docs` - API documentation

---

## Development

### Using Makefile

```bash
# See all available commands
make help

# Install dependencies locally
make install

# Start development server
make dev

# Run tests
make test

# Run with coverage
make test-coverage

# Start Docker services
make docker-up

# Stop Docker services
make docker-down

# View logs
make docker-logs

# Clean build artifacts
make clean
```

### Local Backend Development

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run database (in Docker)
docker-compose up -d postgres

# Start backend
uvicorn main:app --reload

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Local Frontend Development

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.local.example .env.local

# Start development server
npm run dev

# Run tests
npm test
```

---

## Testing

Comprehensive testing guide available in [TESTING.md](./TESTING.md)

### Quick Test Commands

```bash
# Test backend
make backend-test

# Test with coverage
make test-coverage

# Test specific module
cd backend && pytest tests/test_auth.py

# Test with verbose output
cd backend && pytest -v
```

### Test Coverage

The project includes extensive tests:
- **Authentication Tests** - Registration, login, token validation
- **Post CRUD Tests** - Create, read, update, delete operations
- **API Tests** - Health checks, endpoints availability
- **Integration Tests** - Full workflow testing

---

## Configuration

### Environment Variables

#### Backend (`backend/.env`)

```env
# Application
APP_NAME=Fikak App API
DEBUG=true

# Database
DATABASE_URL=postgresql://fikak_user:<your-db-password>@localhost:5432/fikak_db

# JWT
SECRET_KEY=<generate with: openssl rand -hex 32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS S3 (or MinIO for local)
AWS_ACCESS_KEY_ID=<your MINIO_ROOT_USER>
AWS_SECRET_ACCESS_KEY=<your MINIO_ROOT_PASSWORD>
AWS_REGION=us-east-1
S3_BUCKET_NAME=fikak-uploads

# External API
EXTERNAL_API_URL=https://jsonplaceholder.typicode.com

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

#### Frontend (`.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Database Schema

### Users Table
- `id` - Primary key
- `email` - Unique email address
- `username` - Unique username
- `hashed_password` - Bcrypt hashed password
- `is_active` - Account status
- `is_superuser` - Admin flag
- `created_at` - Registration timestamp
- `updated_at` - Last update timestamp

### Posts Table
- `id` - Primary key
- `title` - Post title
- `content` - Post content
- `published` - Publication status
- `user_id` - Foreign key to users
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### File Uploads Table
- `id` - Primary key
- `filename` - Original filename
- `file_key` - S3 object key
- `file_size` - File size in bytes
- `content_type` - MIME type
- `bucket_name` - S3 bucket name
- `user_id` - Foreign key to users
- `created_at` - Upload timestamp

---

## Production Deployment

### Security Checklist

- [ ] Change all default passwords and secrets
- [ ] Generate secure SECRET_KEY: `openssl rand -hex 32`
- [ ] Set `DEBUG=false` in production
- [ ] Use managed PostgreSQL (AWS RDS, etc.)
- [ ] Configure real AWS S3 bucket
- [ ] Enable HTTPS/SSL
- [ ] Configure proper CORS origins
- [ ] Set up rate limiting
- [ ] Enable logging and monitoring
- [ ] Configure automated backups
- [ ] Set up CI/CD pipeline

### Deployment Options

1. **Docker (Recommended)**
   - Use `docker-compose.yml` as base
   - Update environment variables
   - Deploy to any Docker-compatible platform

2. **Cloud Platforms**
   - **Backend**: AWS Lambda, Google Cloud Run, Azure Container Apps
   - **Frontend**: Vercel, Netlify, AWS Amplify
   - **Database**: AWS RDS, Google Cloud SQL, Azure PostgreSQL

3. **Traditional Hosting**
   - Backend: Any VPS with Python support
   - Frontend: Any static hosting or Node.js server
   - Database: Managed PostgreSQL service

---

## Project Structure

```
fikak_app/
├── backend/                    # FastAPI backend
│   ├── tests/                  # Backend tests
│   │   ├── test_auth.py        # Authentication tests
│   │   ├── test_posts.py       # Post CRUD tests
│   │   └── test_api.py         # General API tests
│   ├── main.py                 # Main application
│   ├── auth.py                 # Authentication logic
│   ├── models.py               # Database models
│   ├── schemas.py              # Pydantic schemas
│   ├── database.py             # Database configuration
│   ├── config.py               # App configuration
│   ├── storage.py              # S3 storage client
│   ├── external_api.py         # External API client
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Backend Docker image
│   ├── .env.example            # Environment template
│   └── pytest.ini              # Pytest configuration
├── frontend/                   # Next.js frontend (separate repo)
├── .github/workflows/          # GitHub Actions CI/CD
│   ├── nextjs.yml              # Frontend deployment
│   ├── python-publish.yml      # PyPI publishing
│   └── google-cloudrun-docker.yml  # Cloud Run deployment
├── docker-compose.yml          # Multi-service orchestration
├── Makefile                    # Development commands
├── .env.example                # Environment template
├── README.md                   # This file
├── TESTING.md                  # Comprehensive testing guide
└── SETUP.md                    # Complete setup guide
```

---

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **Pydantic** - Data validation
- **PostgreSQL** - Relational database
- **Boto3** - AWS SDK for Python
- **Jose** - JWT implementation
- **Passlib** - Password hashing
- **Pytest** - Testing framework
- **Uvicorn** - ASGI server

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Zustand** - State management
- **Axios** - HTTP client
- **SWR** - Data fetching

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **PostgreSQL 15** - Database
- **MinIO** - S3-compatible storage
- **GitHub Actions** - CI/CD

---

## Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Verify DATABASE_URL is correct
- Check Docker containers are running: `docker-compose ps`

### Database connection errors
- Ensure PostgreSQL is running: `docker-compose up -d postgres`
- Check credentials in .env match docker-compose.yml
- Wait a few seconds for database to initialize

### File upload fails
- Create bucket in MinIO console (http://localhost:9001)
- Verify AWS credentials in backend/.env
- Check S3_BUCKET_NAME matches created bucket

### Authentication not working
- Verify SECRET_KEY is set in backend/.env
- Check token hasn't expired (30 min default)
- Ensure Authorization header format: `Bearer <token>`

For more troubleshooting, see [TESTING.md](./TESTING.md)

---

## Support

For issues, questions, or contributions:
- Documentation: See [SETUP.md](./SETUP.md) and [TESTING.md](./TESTING.md)
- API Docs: http://localhost:8000/docs (when running)