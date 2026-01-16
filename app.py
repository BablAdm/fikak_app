from flask import Flask, jsonify
import os
import platform
import sys
from datetime import datetime

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/api/info', methods=['GET'])
def info():
    """Application information endpoint"""
    return jsonify({
        'application': 'fikak_app',
        'version': '1.0.0',
        'python_version': sys.version,
        'platform': platform.platform(),
        'hostname': platform.node(),
        'timestamp': datetime.utcnow().isoformat()
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
