"""
Fikak App - Main Application
"""
import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(
    title="Fikak App",
    description="A simple API with health and info endpoints",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.get("/api/info")
async def app_info():
    """
    Application information endpoint.
    """
    return JSONResponse(
        status_code=200,
        content={
            "app_name": "Fikak App",
            "version": "1.0.0",
            "description": "A simple API with health and info endpoints",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
