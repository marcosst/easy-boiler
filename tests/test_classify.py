import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

from app.schemas.llm_output import ResultadoLLM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_apify(video_id: str, subtitle_content: str):
    """Return an AsyncMock that simulates a successful fetch_apify_data call."""
    metadata = {"title": "Test Video", "id": video_id}
    return AsyncMock(return_value=(metadata, subtitle_content))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_classify_creates_knowledge_items(auth_client):
    """POST /htmx/library/{id}/classify processes subtitles and creates knowledge items."""
    subtitle_content = "[00:00:07] selecionar o arquivo\n[00:00:18] salvar o projeto"

    # Save a YouTube library item, mocking Apify so subtitle_path gets set
    with patch("app.main.fetch_apify_data", _mock_apify("dQw4w9WgXcQ", subtitle_content)):
        response = auth_client.post(
            "/htmx/library/save",
            data={
                "subject_id": "1",
                "type": "youtube",
                "name": "Test Video",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "image_path": "",
            },
        )
    assert response.status_code == 200
    # The item was saved and trigger_classify is True, so classify div appears
    assert "/classify" in response.text

    # Mock the LLM classifier
    mock_result = ResultadoLLM(**{
        "itens": [
            {"topico": "Cadastro", "subtopico": "Upload", "acao": "Selecionar arquivo", "timestamp": "00:00:07"},
            {"topico": "Cadastro", "subtopico": "Upload", "acao": "Salvar projeto", "timestamp": "00:00:18"},
        ]
    })

    with patch("app.main.classify_transcript", return_value=mock_result):
        response = auth_client.post("/htmx/library/1/classify")

    assert response.status_code == 200

    # Clean up subtitle file written by the save endpoint
    subs_file = Path("midias/testuser/subtitles/dQw4w9WgXcQ.txt")
    subs_file.unlink(missing_ok=True)


def test_classify_no_subtitle_path(auth_client):
    """POST /htmx/library/{id}/classify with no subtitle_path returns 200 (no-op)."""
    # Save a PDF item (no subtitle_path)
    auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "pdf",
            "name": "Test PDF",
            "file_path": "testuser/pdfs/fake.pdf",
            "image_path": "",
        },
    )

    response = auth_client.post("/htmx/library/1/classify")
    assert response.status_code == 200


def test_classify_nonexistent_item(auth_client):
    """POST /htmx/library/999/classify returns 404."""
    response = auth_client.post("/htmx/library/999/classify")
    assert response.status_code == 404


def test_classify_llm_failure_graceful(auth_client):
    """If LLM fails, endpoint returns 200 with unchanged accordion."""
    subtitle_content = "[00:00:01] test"

    with patch("app.main.fetch_apify_data", _mock_apify("failtest", subtitle_content)):
        auth_client.post(
            "/htmx/library/save",
            data={
                "subject_id": "1",
                "type": "youtube",
                "name": "Fail Video",
                "url": "https://www.youtube.com/watch?v=failtest",
                "image_path": "",
            },
        )

    with patch("app.main.classify_transcript", return_value=None):
        response = auth_client.post("/htmx/library/1/classify")

    assert response.status_code == 200

    # Clean up
    Path("midias/testuser/subtitles/failtest.txt").unlink(missing_ok=True)


def test_save_youtube_triggers_classify_div(auth_client):
    """After saving a YouTube item, the response includes the classify trigger div."""
    subtitle_content = "[00:00:01] intro"

    with patch("app.main.fetch_apify_data", _mock_apify("dQw4w9WgXcQ", subtitle_content)):
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
    assert "hx-post" in response.text
    assert "/classify" in response.text

    # Clean up
    Path("midias/testuser/subtitles/dQw4w9WgXcQ.txt").unlink(missing_ok=True)


def test_save_pdf_does_not_trigger_classify(auth_client):
    """After saving a PDF item, no classify trigger is included."""
    response = auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "pdf",
            "name": "My PDF",
            "file_path": "testuser/pdfs/fake.pdf",
            "image_path": "testuser/thumbnails/fake.jpg",
        },
    )
    assert response.status_code == 200
    assert "/classify" not in response.text


def test_full_classify_updates_content_json(auth_client):
    """Classify endpoint persists knowledge_items and updates content_json."""
    subtitle_content = "[00:00:07] selecionar o arquivo"

    with patch("app.main.fetch_apify_data", _mock_apify("integtest", subtitle_content)):
        auth_client.post(
            "/htmx/library/save",
            data={
                "subject_id": "1",
                "type": "youtube",
                "name": "Integration Test",
                "url": "https://www.youtube.com/watch?v=integtest",
                "image_path": "",
            },
        )

    mock_result = ResultadoLLM(**{
        "itens": [
            {"topico": "Setup", "subtopico": "Inicial", "acao": "Selecionar arquivo", "timestamp": "00:00:07"},
        ]
    })

    with patch("app.main.classify_transcript", return_value=mock_result):
        response = auth_client.post("/htmx/library/1/classify")

    assert response.status_code == 200
    assert "Setup" in response.text
    assert "Selecionar arquivo" in response.text

    # Clean up
    Path("midias/testuser/subtitles/integtest.txt").unlink(missing_ok=True)
