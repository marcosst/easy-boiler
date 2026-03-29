def test_topics_page_returns_200(auth_client):
    response = auth_client.get("/projects/1/collections/11")
    assert response.status_code == 200


def test_topics_page_shows_project_in_header(auth_client):
    # Topics page header shows project name; collection name is not in the header
    response = auth_client.get("/projects/1/collections/11")
    assert "Projeto Alpha" in response.text


def test_topics_page_has_home_link(auth_client):
    # Header logo links back to home
    response = auth_client.get("/projects/1/collections/11")
    assert 'href="/"' in response.text


def test_topics_page_shows_accordion_structure(auth_client):
    response = auth_client.get("/projects/1/collections/11")
    assert "Introdução" in response.text
    assert "Conceitos Fundamentais" in response.text
    assert "Aplicações Práticas" in response.text


def test_topics_page_has_alpine_accordion(auth_client):
    response = auth_client.get("/projects/1/collections/11")
    assert "x-data" in response.text
    assert "x-show" in response.text


def test_topics_page_has_dark_mode_classes(auth_client):
    response = auth_client.get("/projects/1/collections/11")
    assert "dark:bg-neutral-900" in response.text
    assert "dark:bg-neutral-800" in response.text


def test_topics_detail_with_content_is_clickable(auth_client):
    response = auth_client.get("/projects/1/collections/11")
    assert "hx-get" in response.text
    assert "/htmx/details/" in response.text


def test_topics_invalid_project_returns_404(auth_client):
    response = auth_client.get("/projects/999/collections/11")
    assert response.status_code == 404


def test_topics_invalid_collection_returns_404(auth_client):
    response = auth_client.get("/projects/1/collections/999")
    assert response.status_code == 404


def test_htmx_detail_returns_200(auth_client):
    from app.main import MOCK_DETAILS
    detail_id = next(iter(MOCK_DETAILS))
    response = auth_client.get(f"/htmx/details/{detail_id}")
    assert response.status_code == 200


def test_htmx_detail_invalid_returns_404(auth_client):
    response = auth_client.get("/htmx/details/999999")
    assert response.status_code == 404


def test_htmx_detail_renders_youtube_iframe(auth_client):
    from app.main import MOCK_DETAILS
    detail_id = next(
        did for did, d in MOCK_DETAILS.items() if d.get("youtube_url")
    )
    response = auth_client.get(f"/htmx/details/{detail_id}")
    assert "youtube.com/embed" in response.text


def test_htmx_detail_renders_markdown_html(auth_client):
    from app.main import MOCK_DETAILS
    detail_id = next(
        did for did, d in MOCK_DETAILS.items() if d.get("content_md")
    )
    response = auth_client.get(f"/htmx/details/{detail_id}")
    assert "<h2>" in response.text or "<strong>" in response.text


def test_project_page_shows_topics(auth_client):
    # /projects/{id} renders topics (first collection's topics), not collection cards
    response = auth_client.get("/projects/1")
    assert "Introdução" in response.text
