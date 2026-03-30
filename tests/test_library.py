import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient


def test_preview_youtube_returns_preview(auth_client, tmp_path):
    """POST /htmx/library/preview with type=youtube returns preview HTML."""
    mock_oembed_response = MagicMock()
    mock_oembed_response.status_code = 200
    mock_oembed_response.json.return_value = {"title": "Test Video Title"}
    mock_oembed_response.raise_for_status = MagicMock()

    mock_thumb_response = MagicMock()
    mock_thumb_response.status_code = 200
    mock_thumb_response.content = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
    mock_thumb_response.raise_for_status = MagicMock()

    with patch("httpx.get") as mock_get:
        mock_get.side_effect = [mock_oembed_response, mock_thumb_response]
        response = auth_client.post(
            "/htmx/library/preview",
            data={
                "type": "youtube",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "subject_id": "1",
            },
        )

    assert response.status_code == 200
    assert "Test Video Title" in response.text
    assert "Salvar" in response.text


def test_preview_youtube_invalid_url(auth_client):
    """POST /htmx/library/preview with invalid URL returns error."""
    response = auth_client.post(
        "/htmx/library/preview",
        data={
            "type": "youtube",
            "url": "https://notayoutubeurl.com/video",
            "subject_id": "1",
        },
    )
    assert response.status_code == 200
    assert "inválida" in response.text.lower() or "erro" in response.text.lower()


def test_preview_pdf_returns_preview(auth_client, tmp_path):
    """POST /htmx/library/preview with type=pdf returns preview HTML."""
    # Create a minimal valid PDF
    pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"

    response = auth_client.post(
        "/htmx/library/preview",
        data={"type": "pdf", "subject_id": "1"},
        files={"file": ("test-document.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    assert "test-document" in response.text
    assert "Salvar" in response.text


def test_save_youtube_item(auth_client):
    """POST /htmx/library/save creates a library item."""
    response = auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "youtube",
            "name": "My Video",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "image_path": "testuser/thumbnails/fake.jpg",
        },
    )
    assert response.status_code == 200
    assert "My Video" in response.text


def test_save_pdf_item(auth_client):
    """POST /htmx/library/save creates a PDF library item."""
    response = auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "pdf",
            "name": "My Document",
            "file_path": "testuser/pdfs/fake.pdf",
            "image_path": "testuser/thumbnails/fake.jpg",
        },
    )
    assert response.status_code == 200
    assert "My Document" in response.text


def test_save_requires_auth(tmp_path):
    """POST /htmx/library/save without auth redirects."""
    from app.main import app
    client = TestClient(app)
    response = client.post(
        "/htmx/library/save",
        data={"subject_id": "1", "type": "youtube", "name": "X", "url": "http://x.com"},
        follow_redirects=False,
    )
    assert response.status_code == 303
