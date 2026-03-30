from app.md_parser import parse_topics_md


def test_parse_empty_returns_empty_list():
    assert parse_topics_md("") == []
    assert parse_topics_md(None) == []


def test_parse_single_topic():
    md = "# Introdução"
    result = parse_topics_md(md)
    assert len(result) == 1
    assert result[0]["title"] == "Introdução"
    assert result[0]["id"] == "1"
    assert result[0]["subtopics"] == []


def test_parse_full_hierarchy():
    md = """# Tópico 1
## Subtópico 1.1
### Detalhe 1.1.1
Conteúdo do detalhe.
### Detalhe 1.1.2
## Subtópico 1.2
### Detalhe 1.2.1
Mais conteúdo aqui.

Com múltiplas linhas.
# Tópico 2
## Subtópico 2.1
### Detalhe 2.1.1"""
    result = parse_topics_md(md)
    assert len(result) == 2

    t1 = result[0]
    assert t1["title"] == "Tópico 1"
    assert t1["id"] == "1"
    assert len(t1["subtopics"]) == 2

    s1 = t1["subtopics"][0]
    assert s1["title"] == "Subtópico 1.1"
    assert s1["id"] == "1.1"
    assert len(s1["details"]) == 2

    d1 = s1["details"][0]
    assert d1["title"] == "Detalhe 1.1.1"
    assert d1["id"] == "1.1.1"
    assert d1["content_md"] == "Conteúdo do detalhe."
    assert d1["has_content"] is True

    d2 = s1["details"][1]
    assert d2["title"] == "Detalhe 1.1.2"
    assert d2["has_content"] is False

    s2 = t1["subtopics"][1]
    assert s2["id"] == "1.2"
    d_1_2_1 = s2["details"][0]
    assert d_1_2_1["content_md"] == "Mais conteúdo aqui.\n\nCom múltiplas linhas."
    assert d_1_2_1["has_content"] is True

    t2 = result[1]
    assert t2["id"] == "2"
    assert t2["subtopics"][0]["id"] == "2.1"
    assert t2["subtopics"][0]["details"][0]["id"] == "2.1.1"


from app.md_parser import get_detail_content


def test_get_detail_content_found():
    md = "# T\n## S\n### D\nHello world."
    result = get_detail_content(md, "1.1.1")
    assert result == "Hello world."


def test_get_detail_content_not_found():
    md = "# T\n## S\n### D\nHello."
    assert get_detail_content(md, "9.9.9") is None


def test_get_detail_content_empty_md():
    assert get_detail_content(None, "1.1.1") is None
    assert get_detail_content("", "1.1.1") is None
