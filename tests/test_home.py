from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_home_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_home_contains_projetos_title():
    response = client.get("/")
    assert "Projetos" in response.text


def test_home_contains_user_name():
    response = client.get("/")
    assert "Usuário Demo" in response.text


def test_home_contains_project_names():
    response = client.get("/")
    assert "Projeto Alpha" in response.text
    assert "Projeto Beta" in response.text
