from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_topics_page_returns_200():
    response = client.get("/projects/1/collections/11")
    assert response.status_code == 200


def test_topics_page_shows_project_and_collection_in_header():
    response = client.get("/projects/1/collections/11")
    assert "Projeto Alpha" in response.text
    assert "Coleção 2" in response.text


def test_topics_page_has_breadcrumb_link_to_project():
    response = client.get("/projects/1/collections/11")
    assert 'href="/projects/1"' in response.text


def test_topics_page_shows_accordion_structure():
    response = client.get("/projects/1/collections/11")
    assert "Introdução" in response.text
    assert "Conceitos Fundamentais" in response.text
    assert "Aplicações Práticas" in response.text


def test_topics_page_has_alpine_accordion():
    response = client.get("/projects/1/collections/11")
    assert "x-data" in response.text
    assert "x-show" in response.text


def test_topics_page_has_dark_mode_classes():
    response = client.get("/projects/1/collections/11")
    assert "dark:bg-neutral-900" in response.text
    assert "dark:bg-neutral-800" in response.text


def test_topics_detail_with_content_is_clickable():
    response = client.get("/projects/1/collections/11")
    assert "hx-get" in response.text
    assert "/htmx/details/" in response.text


def test_topics_invalid_project_returns_404():
    response = client.get("/projects/999/collections/11")
    assert response.status_code == 404


def test_topics_invalid_collection_returns_404():
    response = client.get("/projects/1/collections/999")
    assert response.status_code == 404


def test_htmx_detail_returns_200():
    from app.main import MOCK_DETAILS
    detail_id = next(iter(MOCK_DETAILS))
    response = client.get(f"/htmx/details/{detail_id}")
    assert response.status_code == 200


def test_htmx_detail_invalid_returns_404():
    response = client.get("/htmx/details/999999")
    assert response.status_code == 404


def test_htmx_detail_renders_youtube_iframe():
    from app.main import MOCK_DETAILS
    detail_id = next(
        did for did, d in MOCK_DETAILS.items() if d.get("youtube_url")
    )
    response = client.get(f"/htmx/details/{detail_id}")
    assert "youtube.com/embed" in response.text


def test_htmx_detail_renders_markdown_html():
    from app.main import MOCK_DETAILS
    detail_id = next(
        did for did, d in MOCK_DETAILS.items() if d.get("content_md")
    )
    response = client.get(f"/htmx/details/{detail_id}")
    assert "<h2>" in response.text or "<strong>" in response.text


def test_collections_cards_link_to_topics():
    response = client.get("/projects/1")
    assert "/projects/1/collections/" in response.text
