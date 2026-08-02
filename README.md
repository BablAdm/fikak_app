# fikak_app

Flask-based API server for the Fikak App.

## Requirements

- Python 3.11+

## Setup

```bash
pip install -r requirements.txt
```

## Running

### Development

```bash
python main.py
```

The server starts on `http://127.0.0.1:5000` by default.

### Production

```bash
gunicorn -b 0.0.0.0:5000 main:app
```

## Configuration

All configuration is via environment variables (a `.env` file is also supported):

| Variable | Default | Description |
|---|---|---|
| `HOST` | `127.0.0.1` | Bind address for the dev server. Set `0.0.0.0` for containers. |
| `PORT` | `5000` | Server port. |
| `DEBUG` | `False` | Set `true` to enable Flask debug mode (never in production). |
| `ALLOWED_ORIGINS` | *(unset)* | Comma-separated CORS origins, e.g. `https://example.com,https://app.example.com`. CORS is disabled when unset. Use `*` only for local development. |

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | API welcome message and version. |
| GET | `/health` | Health check. |
| GET/POST | `/api/test` | Test endpoint; POST echoes a JSON body (400 on invalid JSON). |
