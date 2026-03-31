import pytest
from pydantic import ValidationError
from app.schemas.llm_output import ItemLLM, ResultadoLLM


def test_valid_item():
    item = ItemLLM(topico="Cadastro", subtopico="Upload", acao="Selecionar arquivo", timestamp="00:01:03")
    assert item.topico == "Cadastro"
    assert item.timestamp == "00:01:03"


def test_timestamp_format_invalid():
    with pytest.raises(ValidationError):
        ItemLLM(topico="X", subtopico="Y", acao="Z", timestamp="1:2:3")


def test_timestamp_format_invalid_letters():
    with pytest.raises(ValidationError):
        ItemLLM(topico="X", subtopico="Y", acao="Z", timestamp="ab:cd:ef")


def test_empty_topico_rejected():
    with pytest.raises(ValidationError):
        ItemLLM(topico="", subtopico="Y", acao="Z", timestamp="00:00:00")


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        ItemLLM(topico="X", subtopico="Y", acao="Z", timestamp="00:00:00", url="http://x.com")


def test_resultado_valid():
    data = {
        "itens": [
            {"topico": "A", "subtopico": "B", "acao": "C", "timestamp": "00:00:01"},
            {"topico": "A", "subtopico": "B", "acao": "D", "timestamp": "00:01:00"},
        ]
    }
    result = ResultadoLLM(**data)
    assert len(result.itens) == 2


def test_resultado_extra_fields_rejected():
    with pytest.raises(ValidationError):
        ResultadoLLM(itens=[], extra_field="bad")


def test_whitespace_stripped():
    item = ItemLLM(topico="  Cadastro  ", subtopico=" Upload ", acao=" Acao ", timestamp="00:00:01")
    assert item.topico == "Cadastro"
    assert item.subtopico == "Upload"
    assert item.acao == "Acao"
