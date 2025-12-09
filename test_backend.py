import pytest

from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# test main webpage GET endpoint
def test_get_webpage_invalid_game_id(client):
    response = client.get('/', query_string={'game_id': 'not_a_valid_game_id'})
    assert response.status_code == 400

def test_get_webpage_valid_game_id(client):
    # this is hard because we don't really have a way of testing interactions with the game; thus, generating a valid game id is hard
    pass

def test_get_webpage_no_game_id(client):
    response = client.get('/') # no game id provided as a query param

    assert response.status_code == 400
    assert response.json['message'] == {"game_id": "game_id must be provided."}

# test GET endpoints for info from the backend (used to update the webpage)
def test_get_camera_info_invalid_game_id(client):
    response = client.get('/info', query_string={'game_id': 'not_a_valid_game_id'})
    assert response.status_code == 400

def test_get_camera_info_valid_game_id(client):
    # we're assuming that 12345678 is a valid game id
    response = client.get('/info', query_string={'game_id': '12345678'})
    assert response.status_code == 200
    assert 'x' in response.json
    assert 'y' in response.json

def test_get_camera_info_no_game_id(client):
    response = client.get('/info') # no game id provided as a query param

    assert response.status_code == 400
    assert response.json['message'] == {"game_id": "game_id must be provided."}

# test POST endpoints for submitting data to the backend
# TODO: this will need to interface with the database!
# I'm not writing tests for the json stuff because that's a temporary thing
