# fikak_app

A production-ready Python Flask application designed for deployment on Google Cloud Run.

## Overview

This is a lightweight REST API built with Flask, optimized for containerized deployment on Google Cloud Run. It includes security best practices, health checks, and automated CI/CD via GitHub Actions.

## Features

- **Flask REST API** with multiple endpoints
- **Docker containerization** optimized for Cloud Run
- **Security headers** and best practices
- **Health check endpoint** for monitoring
- **Automated CI/CD** with GitHub Actions
- **Dependency management** with Dependabot
- **Production-ready** with Gunicorn WSGI server
- **Structured logging** for observability

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Welcome message and service info |
| `/health` | GET | Health check endpoint |
| `/api/info` | GET | API information and available endpoints |
| `/api/echo` | POST | Echo back JSON payload |

## Prerequisites

- Python 3.12+
- Docker (for containerized deployment)
- Google Cloud account (for Cloud Run deployment)
- GitHub repository with Actions enabled

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/BablAdm/fikak_app.git
cd fikak_app
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

The application will start on `http://localhost:8080`

### 5. Test the API

```bash
# Health check
curl http://localhost:8080/health

# Get API info
curl http://localhost:8080/api/info

# Echo endpoint
curl -X POST http://localhost:8080/api/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, World!"}'
```

## Docker Deployment

### Build the image

```bash
docker build -t fikak-app .
```

### Run the container

```bash
docker run -p 8080:8080 fikak-app
```

## Google Cloud Run Deployment

### Prerequisites

1. **Enable required APIs:**
   ```bash
   gcloud services enable artifactregistry.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable iamcredentials.googleapis.com
   ```

2. **Create Artifact Registry repository:**
   ```bash
   gcloud artifacts repositories create fikak-app \
     --repository-format=docker \
     --location=us-central1
   ```

3. **Set up Workload Identity Federation** (follow [official guide](https://github.com/google-github-actions/auth#setup))

### Configure GitHub Secrets

Go to your repository **Settings > Secrets and variables > Actions > Variables** and add:

| Variable Name | Description | Example |
|--------------|-------------|---------|
| `GCP_PROJECT_ID` | Your GCP project ID | `my-project-123456` |
| `GCP_REGION` | GCP region for deployment | `us-central1` |
| `CLOUD_RUN_SERVICE` | Cloud Run service name | `fikak-app` |
| `WORKLOAD_IDENTITY_PROVIDER` | Full WIF provider path | `projects/123.../providers/github` |

### Manual Deployment

```bash
# Build and push to Artifact Registry
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT_ID/fikak-app/app:latest

# Deploy to Cloud Run
gcloud run deploy fikak-app \
  --image us-central1-docker.pkg.dev/PROJECT_ID/fikak-app/app:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Automated Deployment

The GitHub Actions workflow (`.github/workflows/google-cloudrun-docker.yml`) automatically deploys to Cloud Run when you push to the `main` branch.

## Project Structure

```
fikak_app/
├── .github/
│   ├── dependabot.yml          # Automated dependency updates
│   └── workflows/
│       └── google-cloudrun-docker.yml  # CI/CD pipeline
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── .gitignore                  # Git ignore rules
├── DEPENDENCY_AUDIT_REPORT.md  # Dependency audit findings
└── README.md                   # This file
```

## Security

### Security Features

- **Non-root container user** - Application runs as unprivileged user
- **Security headers** - HSTS, X-Frame-Options, X-Content-Type-Options
- **Input validation** - JSON payload validation
- **Dependency scanning** - Automated with Dependabot
- **Pinned dependencies** - Exact versions in requirements.txt
- **Health checks** - Container health monitoring

### Reporting Security Issues

Please report security vulnerabilities by opening a GitHub issue with the label `security`.

## Monitoring and Observability

### Logs

Cloud Run automatically captures stdout/stderr logs. View logs in:
- Google Cloud Console: Cloud Run > Service > Logs
- CLI: `gcloud run services logs read fikak-app`

### Health Checks

The `/health` endpoint returns HTTP 200 when the service is healthy:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-16T12:00:00Z"
}
```

### Metrics

Cloud Run provides built-in metrics:
- Request count
- Request latency
- Container CPU/memory utilization
- Container instance count

## Dependency Management

### Automated Updates

Dependabot automatically checks for updates weekly:
- **GitHub Actions** - Every Monday at 09:00
- **Python packages** - Every Monday at 09:00
- **Docker base images** - Every Monday at 09:00

### Manual Updates

```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade package-name

# Update all packages (carefully!)
pip install --upgrade -r requirements.txt

# Freeze updated versions
pip freeze > requirements.txt
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Related Documentation

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

**Version:** 1.0.0
**Last Updated:** 2026-01-16
