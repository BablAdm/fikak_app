"""
Unit tests for Fikak Application
"""
import pytest
import json
from app import app, data_store


@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Reset data store before each test
        data_store['items'] = []
        data_store['requests_count'] = 0
        data_store['next_id'] = 1
        yield client


@pytest.fixture
def sample_item():
    """Create a sample item for testing"""
    return {
        'name': 'Test Item',
        'description': 'This is a test item'
    }


class TestHomeEndpoint:
    """Tests for home endpoint"""

    def test_home_returns_200(self, client):
        """Test that home endpoint returns 200"""
        response = client.get('/')
        assert response.status_code == 200

    def test_home_returns_json(self, client):
        """Test that home endpoint returns JSON"""
        response = client.get('/')
        assert response.content_type == 'application/json'

    def test_home_has_correct_structure(self, client):
        """Test that home endpoint returns correct structure"""
        response = client.get('/')
        data = json.loads(response.data)
        assert 'message' in data
        assert 'status' in data
        assert 'timestamp' in data
        assert 'version' in data
        assert data['status'] == 'running'


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_returns_200(self, client):
        """Test that health endpoint returns 200"""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Test that health endpoint returns healthy status"""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestItemsEndpoint:
    """Tests for items CRUD endpoints"""

    def test_get_items_empty(self, client):
        """Test getting items when none exist"""
        response = client.get('/api/items')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 0
        assert data['items'] == []

    def test_create_item(self, client, sample_item):
        """Test creating a new item"""
        response = client.post(
            '/api/items',
            data=json.dumps(sample_item),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['name'] == sample_item['name']
        assert data['description'] == sample_item['description']
        assert 'id' in data
        assert 'created_at' in data

    def test_create_item_without_name(self, client):
        """Test creating item without required name field"""
        response = client.post(
            '/api/items',
            data=json.dumps({'description': 'No name'}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_items_after_creation(self, client, sample_item):
        """Test getting items after creating one"""
        # Create an item
        client.post(
            '/api/items',
            data=json.dumps(sample_item),
            content_type='application/json'
        )
        # Get all items
        response = client.get('/api/items')
        data = json.loads(response.data)
        assert data['count'] == 1
        assert len(data['items']) == 1
        assert data['items'][0]['name'] == sample_item['name']

    def test_get_specific_item(self, client, sample_item):
        """Test getting a specific item by ID"""
        # Create an item
        create_response = client.post(
            '/api/items',
            data=json.dumps(sample_item),
            content_type='application/json'
        )
        created_item = json.loads(create_response.data)
        item_id = created_item['id']

        # Get the specific item
        response = client.get(f'/api/items/{item_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == item_id
        assert data['name'] == sample_item['name']

    def test_get_nonexistent_item(self, client):
        """Test getting an item that doesn't exist"""
        response = client.get('/api/items/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_delete_item(self, client, sample_item):
        """Test deleting an item"""
        # Create an item
        create_response = client.post(
            '/api/items',
            data=json.dumps(sample_item),
            content_type='application/json'
        )
        created_item = json.loads(create_response.data)
        item_id = created_item['id']

        # Delete the item
        response = client.delete(f'/api/items/{item_id}')
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get(f'/api/items/{item_id}')
        assert get_response.status_code == 404

    def test_delete_nonexistent_item(self, client):
        """Test deleting an item that doesn't exist"""
        response = client.delete('/api/items/999')
        assert response.status_code == 404


class TestStatsEndpoint:
    """Tests for stats endpoint"""

    def test_stats_initial(self, client):
        """Test stats endpoint with no items"""
        response = client.get('/api/stats')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total_items'] == 0
        assert 'total_requests' in data
        assert 'timestamp' in data

    def test_stats_after_items_created(self, client, sample_item):
        """Test stats endpoint after creating items"""
        # Create two items
        client.post(
            '/api/items',
            data=json.dumps(sample_item),
            content_type='application/json'
        )
        client.post(
            '/api/items',
            data=json.dumps({'name': 'Second Item'}),
            content_type='application/json'
        )

        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert data['total_items'] == 2


class TestErrorHandlers:
    """Tests for error handlers"""

    def test_404_error(self, client):
        """Test 404 error handler"""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
