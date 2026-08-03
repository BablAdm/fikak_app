import pytest
import json
import os
from main import app


@pytest.fixture
def client():
    """Fixture to provide a Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def env_var(monkeypatch):
    """Fixture to set environment variables for testing."""
    def set_env(key, value):
        monkeypatch.setenv(key, value)
    return set_env


class TestHomeEndpoint:
    """Tests for the root endpoint."""

    def test_home_returns_200(self, client):
        """Test that home endpoint returns 200 OK."""
        response = client.get('/')
        assert response.status_code == 200

    def test_home_returns_json(self, client):
        """Test that home endpoint returns valid JSON."""
        response = client.get('/')
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_home_has_required_fields(self, client):
        """Test that home endpoint response has required fields."""
        response = client.get('/')
        data = json.loads(response.data)
        assert 'status' in data
        assert 'message' in data
        assert 'version' in data
        assert data['status'] == 'success'

    def test_home_has_version(self, client):
        """Test that home endpoint returns version."""
        response = client.get('/')
        data = json.loads(response.data)
        assert data['version'] == '1.0.0'


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client):
        """Test that health endpoint returns 200 OK."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_returns_healthy(self, client):
        """Test that health endpoint returns healthy status."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_health_returns_service_name(self, client):
        """Test that health endpoint returns service name."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['service'] == 'fikak_app'


class TestTestEndpoint:
    """Tests for the test endpoint."""

    def test_test_get_returns_200(self, client):
        """Test that GET /api/test returns 200 OK."""
        response = client.get('/api/test')
        assert response.status_code == 200

    def test_test_get_returns_message(self, client):
        """Test that GET /api/test returns expected message."""
        response = client.get('/api/test')
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['message'] == 'GET request received'

    def test_test_post_valid_json_returns_200(self, client):
        """Test that POST /api/test with valid JSON returns 200."""
        response = client.post(
            '/api/test',
            data=json.dumps({'key': 'value'}),
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_test_post_valid_json_echoes_data(self, client):
        """Test that POST /api/test echoes the data."""
        test_data = {'ping': 'pong', 'number': 42}
        response = client.post(
            '/api/test',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['data'] == test_data

    def test_test_post_invalid_json_returns_400(self, client):
        """Test that POST /api/test with invalid JSON returns 400."""
        response = client.post(
            '/api/test',
            data='not-valid-json',
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_test_post_invalid_json_returns_error(self, client):
        """Test that POST /api/test with invalid JSON returns error message."""
        response = client.post(
            '/api/test',
            data='not-valid-json',
            content_type='application/json'
        )
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Invalid JSON' in data['message']

    def test_test_post_empty_json_returns_400(self, client):
        """Test that POST /api/test with empty body returns 400."""
        response = client.post(
            '/api/test',
            data='',
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_test_post_complex_json(self, client):
        """Test that POST /api/test handles complex JSON structures."""
        test_data = {
            'nested': {'key': 'value'},
            'array': [1, 2, 3],
            'string': 'test',
            'number': 123,
            'boolean': True,
            'null': None
        }
        response = client.post(
            '/api/test',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data'] == test_data


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self, client):
        """Test that 404 error handler returns proper JSON."""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()

    def test_404_returns_json(self, client):
        """Test that 404 response is valid JSON."""
        response = client.get('/nonexistent/path/deep')
        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'status' in data


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_disabled_by_default(self, client):
        """Test that CORS is disabled when ALLOWED_ORIGINS not set."""
        # Send a request with an Origin header (required for CORS to work)
        response = client.get('/', headers={'Origin': 'http://example.com'})
        # When CORS is not enabled, there should be no CORS headers
        assert 'Access-Control-Allow-Origin' not in response.headers

    def test_cors_disabled_without_origin_header(self, client):
        """Test that CORS headers are not sent without an Origin header."""
        response = client.get('/')
        # Even if CORS is enabled, without Origin header no ACAO header
        assert 'Access-Control-Allow-Origin' not in response.headers

    def test_cors_options_request_rejected(self, client):
        """Test that OPTIONS preflight requests are rejected when CORS disabled."""
        response = client.options('/', headers={'Origin': 'http://example.com'})
        # Without CORS enabled, preflight should not succeed
        assert response.status_code == 405 or 'Access-Control-Allow-Origin' not in response.headers


class TestContentTypes:
    """Tests for content type handling."""

    def test_responses_are_json(self, client):
        """Test that all success responses are JSON."""
        endpoints = ['/', '/health', '/api/test']
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.content_type == 'application/json' or 'application/json' in response.content_type

    def test_error_responses_are_json(self, client):
        """Test that error responses are JSON."""
        response = client.get('/nonexistent')
        assert response.content_type == 'application/json' or 'application/json' in response.content_type


class TestHttpMethods:
    """Tests for HTTP method handling."""

    def test_post_not_allowed_on_home(self, client):
        """Test that POST is not allowed on home endpoint."""
        response = client.post('/')
        assert response.status_code == 405

    def test_post_not_allowed_on_health(self, client):
        """Test that POST is not allowed on health endpoint."""
        response = client.post('/health')
        assert response.status_code == 405

    def test_put_not_allowed(self, client):
        """Test that PUT is not allowed on test endpoint."""
        response = client.put('/api/test')
        assert response.status_code == 405

    def test_delete_not_allowed(self, client):
        """Test that DELETE is not allowed on test endpoint."""
        response = client.delete('/api/test')
        assert response.status_code == 405
