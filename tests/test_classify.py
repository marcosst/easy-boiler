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


def _mock_llm_result(items):
    """Return a ResultadoLLM from a list of dicts."""
    return ResultadoLLM(itens=items)


# ---------------------------------------------------------------------------
# Save endpoint — inline classify
# ---------------------------------------------------------------------------

def test_save_youtube_classifies_inline(auth_client):
    """POST /htmx/library/save with YouTube runs LLM classification inline."""
    subtitle_content = "[00:00:07] selecionar o arquivo\n[00:00:18] salvar o projeto"

    mock_result = _mock_llm_result([
        {"topico": "Cadastro", "subtopico": "Upload", "acao": "Selecionar arquivo", "timestamp": "00:00:07"},
        {"topico": "Cadastro", "subtopico": "Upload", "acao": "Salvar projeto", "timestamp": "00:00:18"},
    ])

    with patch("app.main.fetch_apify_data", _mock_apify("dQw4w9WgXcQ", subtitle_content)), \
         patch("app.main.classify_transcript", return_value=mock_result):
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
    # Response should contain the library item
    assert "Test Video" in response.text
    # Response should trigger topics refresh via HX-Trigger
    assert "refresh-topics" in response.headers.get("hx-trigger", "")

    Path("midias/testuser/subtitles/dQw4w9WgXcQ.txt").unlink(missing_ok=True)


def test_save_youtube_llm_failure_still_saves_item(auth_client):
    """If LLM fails during save, the item is still saved but no topics generated."""
    subtitle_content = "[00:00:01] test content"

    with patch("app.main.fetch_apify_data", _mock_apify("failtest", subtitle_content)), \
         patch("app.main.classify_transcript", return_value=None):
        response = auth_client.post(
            "/htmx/library/save",
            data={
                "subject_id": "1",
                "type": "youtube",
                "name": "Fail Video",
                "url": "https://www.youtube.com/watch?v=failtest",
                "image_path": "",
            },
        )

    assert response.status_code == 200
    assert "Fail Video" in response.text
    # No refresh-topics trigger when LLM fails
    assert "refresh-topics" not in response.headers.get("hx-trigger", "")

    Path("midias/testuser/subtitles/failtest.txt").unlink(missing_ok=True)


def test_save_pdf_does_not_classify(auth_client):
    """After saving a PDF item, no classification happens."""
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
    assert "hx-swap-oob" not in response.text


# ---------------------------------------------------------------------------
# Classify endpoint — still works for reprocessing
# ---------------------------------------------------------------------------

def test_classify_endpoint_works(auth_client):
    """POST /htmx/library/{id}/classify can reprocess an existing item."""
    subtitle_content = "[00:00:07] selecionar o arquivo"

    with patch("app.main.fetch_apify_data", _mock_apify("reprocess1", subtitle_content)):
        auth_client.post(
            "/htmx/library/save",
            data={
                "subject_id": "1",
                "type": "youtube",
                "name": "Reprocess Test",
                "url": "https://www.youtube.com/watch?v=reprocess1",
                "image_path": "",
            },
        )

    mock_result = _mock_llm_result([
        {"topico": "Setup", "subtopico": "Inicial", "acao": "Selecionar arquivo", "timestamp": "00:00:07"},
    ])

    with patch("app.main.classify_transcript", return_value=mock_result):
        response = auth_client.post("/htmx/library/1/classify")

    assert response.status_code == 200
    assert "Setup" in response.text

    Path("midias/testuser/subtitles/reprocess1.txt").unlink(missing_ok=True)


def test_classify_nonexistent_item(auth_client):
    """POST /htmx/library/999/classify returns 404."""
    response = auth_client.post("/htmx/library/999/classify")
    assert response.status_code == 404


def test_classify_no_subtitle_path(auth_client):
    """POST /htmx/library/{id}/classify with no subtitle_path returns 200 (no-op)."""
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
