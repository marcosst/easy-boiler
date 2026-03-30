from app.i18n import translate, SUPPORTED_LANGS


def test_translate_returns_portuguese_string():
    assert translate("header.profile", "pt") == "Meu Perfil"


def test_translate_returns_english_string():
    assert translate("header.profile", "en") == "My Profile"


def test_translate_returns_spanish_string():
    assert translate("header.profile", "es") == "Mi Perfil"


def test_translate_falls_back_to_pt_for_missing_key():
    result = translate("header.profile", "xx")
    assert result == "Meu Perfil"


def test_translate_returns_key_when_not_found_anywhere():
    assert translate("nonexistent.key", "en") == "nonexistent.key"


def test_supported_langs():
    assert SUPPORTED_LANGS == {"en", "pt", "es"}


from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from app.i18n.middleware import LanguageMiddleware


def _make_test_app():
    """Minimal Starlette app with LanguageMiddleware for isolated testing."""
    async def homepage(request):
        return PlainTextResponse(request.state.lang)

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(LanguageMiddleware)
    return TestClient(app)


def test_middleware_defaults_to_pt():
    client = _make_test_app()
    resp = client.get("/")
    assert resp.text == "pt"


def test_middleware_reads_query_param():
    client = _make_test_app()
    resp = client.get("/?lang=en", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.cookies.get("lang") == "en"


def test_middleware_reads_cookie():
    client = _make_test_app()
    client.cookies.set("lang", "es")
    resp = client.get("/")
    assert resp.text == "es"


def test_middleware_reads_accept_language():
    client = _make_test_app()
    resp = client.get("/", headers={"Accept-Language": "en-US,en;q=0.9,pt;q=0.8"})
    assert resp.text == "en"


def test_middleware_ignores_unsupported_lang_param():
    client = _make_test_app()
    resp = client.get("/?lang=fr", follow_redirects=False)
    assert resp.status_code == 200
    assert resp.text == "pt"


def test_set_language_saves_cookie_and_refreshes(auth_client):
    resp = auth_client.post(
        "/htmx/set-language",
        data={"lang": "en"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Refresh") == "true"
    assert resp.cookies.get("lang") == "en"


def test_set_language_rejects_invalid(auth_client):
    resp = auth_client.post(
        "/htmx/set-language",
        data={"lang": "fr"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
