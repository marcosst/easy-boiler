def test_project_topics_returns_200(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert response.status_code == 200


def test_project_topics_shows_project_name(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "Projeto Teste" in response.text


def test_project_topics_has_home_link(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert 'href="/"' in response.text


def test_project_topics_shows_accordion_structure(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "Introdução" in response.text
    assert "Conceitos Fundamentais" in response.text
    assert "Aplicações Práticas" in response.text


def test_project_topics_has_alpine_accordion(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "x-data" in response.text
    assert "x-show" in response.text


def test_project_topics_has_dark_mode_classes(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "dark:bg-neutral-900" in response.text
    assert "dark:bg-neutral-800" in response.text


def test_project_topics_detail_is_clickable(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "hx-get" in response.text
    assert "/htmx/details/testuser/projeto-teste/" in response.text


def test_project_topics_unknown_project_returns_404(auth_client):
    response = auth_client.get("/testuser/nonexistent")
    assert response.status_code == 404


def test_project_topics_unknown_user_returns_404(auth_client):
    response = auth_client.get("/nobody/projeto-teste")
    assert response.status_code == 404


def test_htmx_detail_returns_200(auth_client):
    response = auth_client.get("/htmx/details/testuser/projeto-teste/1.1.1")
    assert response.status_code == 200


def test_htmx_detail_invalid_returns_404(auth_client):
    response = auth_client.get("/htmx/details/testuser/projeto-teste/9.9.9")
    assert response.status_code == 404


def test_htmx_detail_renders_markdown_html(auth_client):
    response = auth_client.get("/htmx/details/testuser/projeto-teste/1.1.1")
    assert "<strong>" in response.text or "<em>" in response.text
