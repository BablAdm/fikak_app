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
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'name field is required'}), 400

        item = {
            'id': data_store['next_id'],
            'name': data['name'],
            'description': data.get('description', ''),
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
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Development server only - use gunicorn in production (see Dockerfile)
    # NOTE: This Flask development server should NEVER be used in production.
    # For production deployments, the Dockerfile uses Gunicorn with proper security settings.
    port = int(os.environ.get('PORT', 8080))

    logger.info(f"Starting Fikak Application on port {port}")
    # Always disable debug mode - development server is not for production use
    # Use Dockerfile with Gunicorn for any actual deployment (see Dockerfile)
    app.run(host='127.0.0.1', port=port, debug=False)
