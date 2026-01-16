from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '0.0.0.0')
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
        data = request.get_json()
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
    print(f"Starting Fikak App server on {HOST}:{PORT}")
    print(f"Debug mode: {DEBUG}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
