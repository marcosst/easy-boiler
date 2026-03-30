def test_subject_topics_returns_200(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert response.status_code == 200


def test_subject_topics_shows_subject_name(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert "Assunto Teste" in response.text


def test_subject_topics_has_home_link(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert 'href="/"' in response.text


def test_subject_topics_shows_accordion_structure(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert "Introdução" in response.text
    assert "Conceitos Fundamentais" in response.text
    assert "Aplicações Práticas" in response.text


def test_subject_topics_has_alpine_accordion(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert "x-data" in response.text
    assert "x-show" in response.text


def test_subject_topics_has_dark_mode_classes(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert "dark:bg-neutral-900" in response.text
    assert "dark:bg-neutral-800" in response.text


def test_subject_topics_detail_is_clickable(auth_client):
    response = auth_client.get("/testuser/assunto-teste")
    assert "hx-get" in response.text
    assert "/htmx/details/testuser/assunto-teste/" in response.text


def test_subject_topics_unknown_subject_returns_404(auth_client):
    response = auth_client.get("/testuser/nonexistent")
    assert response.status_code == 404


def test_subject_topics_unknown_user_returns_404(auth_client):
    response = auth_client.get("/nobody/assunto-teste")
    assert response.status_code == 404


def test_htmx_detail_returns_200(auth_client):
    response = auth_client.get("/htmx/details/testuser/assunto-teste/1.1.1")
    assert response.status_code == 200


def test_htmx_detail_invalid_returns_404(auth_client):
    response = auth_client.get("/htmx/details/testuser/assunto-teste/9.9.9")
    assert response.status_code == 404


def test_htmx_detail_renders_markdown_html(auth_client):
    response = auth_client.get("/htmx/details/testuser/assunto-teste/1.1.1")
    assert "<strong>" in response.text or "<em>" in response.text
