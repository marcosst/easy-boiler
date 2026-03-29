from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_collections_returns_200():
    response = client.get("/projects/1")
    assert response.status_code == 200


def test_collections_returns_404_for_unknown_project():
    response = client.get("/projects/999")
    assert response.status_code == 404


def test_collections_contains_project_name():
    response = client.get("/projects/1")
    assert "Projeto Alpha" in response.text


def test_collections_contains_collection_names():
    response = client.get("/projects/1")
    assert "Coleção 1" in response.text
    assert "Coleção 2" in response.text
