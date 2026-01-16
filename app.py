"""
fikak_app - A simple Flask application for Google Cloud Run
"""
import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Application version
VERSION = "1.0.0"


@app.route('/')
def index():
    """Root endpoint - Welcome message"""
    return jsonify({
        "service": "fikak_app",
        "version": VERSION,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "Welcome to fikak_app API"
    })


@app.route('/health')
def health():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200


@app.route('/api/info')
def info():
    """API information endpoint"""
    return jsonify({
        "service": "fikak_app",
        "version": VERSION,
        "endpoints": {
            "root": "/",
            "health": "/health",
            "info": "/api/info",
            "echo": "/api/echo (POST)"
        },
        "environment": {
            "python_version": os.sys.version.split()[0],
            "port": os.environ.get('PORT', '8080')
        }
    })


@app.route('/api/echo', methods=['POST'])
def echo():
    """Echo endpoint - returns the posted JSON data"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({
                "error": "No JSON data provided"
            }), 400

        return jsonify({
            "echo": data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    except Exception as e:
        logger.error(f"Error in echo endpoint: {str(e)}")
        return jsonify({
            "error": "Invalid JSON data"
        }), 400


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist",
        "status": 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "status": 500
    }), 500


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    """Handle all HTTP exceptions"""
    return jsonify({
        "error": error.name,
        "message": error.description,
        "status": error.code
    }), error.code


@app.before_request
def log_request():
    """Log incoming requests"""
    logger.info(f"{request.method} {request.path} from {request.remote_addr}")


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


if __name__ == '__main__':
    # This is used when running locally only
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting fikak_app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
