"""
Fikak Application - A simple Flask web application for testing
"""
import os
import logging
from flask import Flask, jsonify, request
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure Flask security settings
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1MB max request size
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Don't cache responses by default

# Set security headers to prevent common attacks
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Store for demo purposes (in-memory)
# Note: In production, use a real database. This demo is single-worker only (see Dockerfile).
data_store = {
    'items': [],
    'requests_count': 0,
    'next_id': 1
}


@app.route('/')
def home():
    """Home endpoint"""
    data_store['requests_count'] += 1
    return jsonify({
        'message': 'Welcome to Fikak Application',
        'status': 'running',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0',
        'total_requests': data_store['requests_count']
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200


@app.route('/api/items', methods=['GET', 'POST'])
def items():
    """CRUD endpoint for items"""
    data_store['requests_count'] += 1

    if request.method == 'GET':
        return jsonify({
            'items': data_store['items'],
            'count': len(data_store['items'])
        })

    elif request.method == 'POST':
        try:
            data = request.get_json(silent=True)
        except Exception:
            return jsonify({'error': 'Invalid JSON'}), 400

        if not data or 'name' not in data:
            return jsonify({'error': 'name field is required'}), 400

        name = data.get('name', '').strip() if isinstance(data.get('name'), str) else ''
        if not name:
            return jsonify({'error': 'name field is required'}), 400

        item = {
            'id': data_store['next_id'],
            'name': name,
            'description': str(data.get('description', '')).strip() if isinstance(data.get('description'), str) else '',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        data_store['items'].append(item)
        data_store['next_id'] += 1
        logger.info(f"Created new item with ID {item['id']}")

        return jsonify(item), 201


@app.route('/api/items/<int:item_id>', methods=['GET', 'DELETE'])
def item_detail(item_id):
    """Get or delete specific item"""
    data_store['requests_count'] += 1

    item = next((item for item in data_store['items'] if item['id'] == item_id), None)

    if request.method == 'GET':
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        return jsonify(item)

    elif request.method == 'DELETE':
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        data_store['items'].remove(item)
        logger.info(f"Item deleted successfully")
        return jsonify({'message': 'Item deleted successfully'}), 200


@app.route('/api/stats')
def stats():
    """Get application statistics"""
    return jsonify({
        'total_items': len(data_store['items']),
        'total_requests': data_store['requests_count'],
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error("Internal server error occurred")
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle unhandled exceptions"""
    logger.error("Unhandled exception occurred")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Development server only - use gunicorn in production (see Dockerfile)
    # NOTE: This Flask development server should NEVER be used in production.
    # For production deployments, the Dockerfile uses Gunicorn with proper security settings.
    try:
        port = int(os.environ.get('PORT', '8080'))
    except (ValueError, TypeError):
        port = 8080
        logger.warning("Invalid PORT environment variable, using default 8080")

    if port < 1 or port > 65535:
        port = 8080
        logger.warning("PORT out of valid range, using default 8080")

    logger.info(f"Starting Fikak Application on port {port}")
    # Always disable debug mode - development server is not for production use
    # Use Dockerfile with Gunicorn for any actual deployment (see Dockerfile)
    app.run(host='127.0.0.1', port=port, debug=False)
