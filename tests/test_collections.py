def test_collections_returns_200(auth_client):
    response = auth_client.get("/projects/1")
    assert response.status_code == 200


def test_collections_returns_404_for_unknown_project(auth_client):
    response = auth_client.get("/projects/999")
    assert response.status_code == 404


def test_collections_contains_project_name(auth_client):
    response = auth_client.get("/projects/1")
    assert "Projeto Alpha" in response.text


def test_collections_page_shows_topics(auth_client):
    # /projects/{id} renders topics page (first collection's topics)
    response = auth_client.get("/projects/1")
    assert "Tópicos" in response.text or "Introdução" in response.text
