def test_home_returns_200(auth_client):
    response = auth_client.get("/")
    assert response.status_code == 200


def test_home_contains_projetos_title(auth_client):
    response = auth_client.get("/")
    assert "Projetos" in response.text


def test_home_contains_user_name(auth_client):
    response = auth_client.get("/")
    assert "testuser" in response.text


def test_home_contains_project_names(auth_client):
    response = auth_client.get("/")
    assert "Projeto Alpha" in response.text
    assert "Projeto Beta" in response.text
