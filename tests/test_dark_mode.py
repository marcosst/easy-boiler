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
    assert "dark:bg-slate-900" in response.text
