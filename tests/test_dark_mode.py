from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_home_contains_tailwind_dark_mode_config():
    response = client.get("/")
    assert "darkMode" in response.text


def test_home_contains_theme_manager():
    response = client.get("/")
    assert "x-data" in response.text
    assert "setTheme" in response.text


def test_home_has_dark_body_class():
    response = client.get("/")
    assert "dark:bg-neutral-900" in response.text


def test_dropdown_contains_tema_toggle():
    response = client.get("/")
    assert "Tema" in response.text


def test_dropdown_contains_theme_options():
    response = client.get("/")
    assert "Claro" in response.text
    assert "Escuro" in response.text
    assert "Auto" in response.text


def test_home_cards_have_dark_classes():
    response = client.get("/")
    assert "dark:bg-neutral-800" in response.text
    assert "dark:border-neutral-700" in response.text


def test_collections_cards_have_dark_classes():
    response = client.get("/projects/1")
    assert "dark:bg-neutral-800" in response.text
    assert "dark:border-neutral-700" in response.text


def test_home_section_title_has_dark_class():
    response = client.get("/")
    assert "dark:text-neutral-100" in response.text


def test_collections_section_title_has_dark_class():
    response = client.get("/projects/1")
    assert "dark:text-neutral-100" in response.text
