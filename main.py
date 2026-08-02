from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
# Configure CORS - requires ALLOWED_ORIGINS environment variable
# For development, set ALLOWED_ORIGINS=* explicitly
# For production, set specific origins: ALLOWED_ORIGINS=https://example.com,https://app.example.com
allowed_origins_str = os.getenv('ALLOWED_ORIGINS', '')
if allowed_origins_str:
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',') if origin.strip()]
    CORS(app, origins=allowed_origins)
else:
    # No CORS enabled by default for security
    app.logger.warning('CORS not configured. Set ALLOWED_ORIGINS environment variable to enable.')

# Configuration
# HOST defaults to localhost; container/production deployments must set HOST=0.0.0.0 explicitly
PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '127.0.0.1')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

@app.route('/')
def home():
    return jsonify({
        'status': 'success',
        'message': 'Welcome to Fikak App API',
        'version': '1.0.0'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'fikak_app'
    })

@app.route('/api/test', methods=['GET', 'POST'])
def test():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({
                'status': 'error',
                'message': 'Invalid JSON payload'
            }), 400
        return jsonify({
            'status': 'success',
            'message': 'POST request received',
            'data': data
        })
    return jsonify({
        'status': 'success',
        'message': 'GET request received'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Fikak App server on {HOST}:{PORT}")
    logger.info(f"Debug mode: {DEBUG}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
