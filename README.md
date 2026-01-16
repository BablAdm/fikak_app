# Fikak Application

A simple Flask REST API application with Docker support for easy deployment and testing.

## Features

- RESTful API with CRUD operations
- Health check endpoint
- Request tracking and statistics
- Comprehensive test suite
- Docker containerization
- Production-ready with Gunicorn

## Quick Start

### Using Docker (Recommended)

Build and run the container:

```bash
# Build the image
docker build -t fikak_app .

# Run the container
docker run -p 8080:8080 fikak_app
```

### Using Docker Compose

```bash
# Run production version
docker-compose up fikak_app

# Run development version (with hot reload)
docker-compose up fikak_app_dev
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## API Endpoints

### Home
- **GET** `/` - Welcome message and app status

### Health Check
- **GET** `/health` - Health check endpoint (returns 200 if healthy)

### Items Management
- **GET** `/api/items` - Get all items
- **POST** `/api/items` - Create a new item
  ```json
  {
    "name": "Item Name",
    "description": "Item Description"
  }
  ```
- **GET** `/api/items/<id>` - Get specific item
- **DELETE** `/api/items/<id>` - Delete an item

### Statistics
- **GET** `/api/stats` - Get application statistics

## Testing

### Run Unit Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html
```

### Manual API Testing

```bash
# Check health
curl http://localhost:8080/health

# Get home page
curl http://localhost:8080/

# Create an item
curl -X POST http://localhost:8080/api/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Item", "description": "This is a test"}'

# Get all items
curl http://localhost:8080/api/items

# Get statistics
curl http://localhost:8080/api/stats
```

## Environment Variables

- `PORT` - Port to run the application on (default: 8080)
- `DEBUG` - Enable debug mode (default: False)

## Docker Commands Reference

```bash
# Build the image
docker build -t fikak_app .

# Run the container
docker run -p 8080:8080 fikak_app

# Run with environment variables
docker run -p 8080:8080 -e DEBUG=True fikak_app

# Run in detached mode
docker run -d -p 8080:8080 --name fikak_app fikak_app

# View logs
docker logs fikak_app

# Stop the container
docker stop fikak_app

# Remove the container
docker rm fikak_app
```

## Production Deployment

The application uses Gunicorn as the WSGI server for production deployments. It's configured with:
- 2 workers
- 4 threads per worker
- 60-second timeout
- Health check every 30 seconds

## Project Structure

```
fikak_app/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── .dockerignore         # Docker ignore file
├── .gitignore           # Git ignore file
├── pytest.ini           # Pytest configuration
├── README.md            # This file
└── tests/               # Test directory
    ├── __init__.py
    └── test_app.py      # Application tests
```

## License

MIT