from fastapi import FastAPI
from datetime import datetime
import os
import sys

app = FastAPI(title="Fikak App", version="1.0.0")


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/info")
async def info():
    """
    Application information endpoint.
    """
    return {
        "application": "Fikak App",
        "version": "1.0.0",
        "python_version": sys.version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
