#!/usr/bin/env python3
"""
Flask API server with health, echo, and info endpoints
"""

from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/echo', methods=['POST'])
def echo():
    """Echo endpoint that returns the posted JSON data"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({
                'error': 'Invalid JSON or no data provided'
            }), 400

        return jsonify(data), 200
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400


@app.route('/api/info', methods=['GET'])
def info():
    """Info endpoint that returns application information"""
    return jsonify({
        'application': 'fikak_app',
        'version': '1.0.0',
        'description': 'Flask API server with health, echo, and info endpoints',
        'endpoints': {
            '/health': {
                'method': 'GET',
                'description': 'Health check endpoint'
            },
            '/api/echo': {
                'method': 'POST',
                'description': 'Echoes back the JSON data sent in the request body'
            },
            '/api/info': {
                'method': 'GET',
                'description': 'Returns application information and available endpoints'
            }
        },
        'timestamp': datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
