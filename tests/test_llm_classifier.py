import json
from unittest.mock import patch, MagicMock
import pytest
from app.services.llm_classifier import classify_transcript, _build_messages
from app.schemas.llm_output import ResultadoLLM


def test_build_messages_empty_taxonomy():
    taxonomy = {"topicos": []}
    transcript = "[00:00:07] selecionar o arquivo\n[00:00:18] salvar o projeto"
    messages = _build_messages(taxonomy, transcript)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Nenhuma taxonomia existente" in messages[1]["content"]
    assert "[00:00:07]" in messages[1]["content"]


def test_build_messages_with_taxonomy():
    taxonomy = {
        "topicos": [
            {"titulo": "Cadastro", "subtopicos": ["Upload", "Config"]}
        ]
    }
    transcript = "[00:00:07] selecionar o arquivo"
    messages = _build_messages(taxonomy, transcript)
    assert "Cadastro" in messages[1]["content"]
    assert "Upload" in messages[1]["content"]


def test_classify_transcript_success():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "itens": [
            {"topico": "Cadastro", "subtopico": "Upload", "acao": "Selecionar arquivo", "timestamp": "00:00:07"}
        ]
    })

    with patch("app.services.llm_classifier._call_openai", return_value=mock_response):
        result = classify_transcript(
            taxonomy={"topicos": []},
            transcript="[00:00:07] selecionar o arquivo",
        )
    assert isinstance(result, ResultadoLLM)
    assert len(result.itens) == 1
    assert result.itens[0].topico == "Cadastro"


def test_classify_transcript_invalid_json():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json"

    with patch("app.services.llm_classifier._call_openai", return_value=mock_response):
        result = classify_transcript(
            taxonomy={"topicos": []},
            transcript="[00:00:07] selecionar o arquivo",
        )
    assert result is None


def test_classify_transcript_pydantic_validation_error():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "itens": [
            {"topico": "", "subtopico": "X", "acao": "Y", "timestamp": "00:00:01"}
        ]
    })

    with patch("app.services.llm_classifier._call_openai", return_value=mock_response):
        result = classify_transcript(
            taxonomy={"topicos": []},
            transcript="[00:00:07] selecionar o arquivo",
        )
    assert result is None
