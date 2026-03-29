def test_home_redirects_to_username(auth_client):
    response = auth_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/testuser"


def test_username_route_returns_200(auth_client):
    response = auth_client.get("/testuser")
    assert response.status_code == 200


def test_username_route_contains_projetos_title(auth_client):
    response = auth_client.get("/testuser")
    assert "Projetos" in response.text


def test_username_route_contains_user_name(auth_client):
    response = auth_client.get("/testuser")
    assert "testuser" in response.text


def test_username_route_shows_db_projects(auth_client):
    response = auth_client.get("/testuser")
    assert "Projeto Teste" in response.text
    assert "Segundo Projeto" in response.text


def test_username_route_unknown_user_returns_404(auth_client):
    response = auth_client.get("/nobody")
    assert response.status_code == 404
