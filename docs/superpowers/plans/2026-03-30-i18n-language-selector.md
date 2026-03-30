# i18n Language Selector (EN/PT/ES) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-language support (EN/PT/ES) with language selector in user menu and public pages, translating all hardcoded Portuguese strings.

**Architecture:** JSON translation files loaded at startup, exposed as Jinja2 global `_()`. A FastAPI middleware resolves language per-request (query param > cookie > DB > Accept-Language > fallback pt). Language selector uses flag icons inline in menu (logged in) and top-right corner (public pages).

**Tech Stack:** FastAPI, Jinja2, HTMX, Alpine.js, aiosqlite, dbmate migrations

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `app/i18n/__init__.py` | Load JSON translations, expose `translate()` function, register Jinja2 global |
| Create | `app/i18n/pt.json` | Portuguese translations (base) |
| Create | `app/i18n/en.json` | English translations |
| Create | `app/i18n/es.json` | Spanish translations |
| Create | `app/i18n/middleware.py` | Language resolution middleware |
| Create | `app/templates/partials/language_selector.html` | Reusable flag selector component |
| Create | `db/migrations/YYYYMMDDHHMMSS_add_language_to_users.sql` | Add `language` column to users |
| Create | `tests/test_i18n.py` | Tests for i18n module, middleware, and route |
| Modify | `app/main.py` | Register middleware, add `/htmx/set-language` route, use `_()` for error strings |
| Modify | `app/auth.py:23-31` | Use translation keys for `validate_username` errors |
| Modify | `app/templates/base.html:2` | Dynamic `lang` attribute |
| Modify | `app/templates/partials/header.html` | Replace hardcoded strings with `_()`, add language selector |
| Modify | `app/templates/home.html` | Replace hardcoded strings with `_()` |
| Modify | `app/templates/topics.html` | Replace hardcoded strings with `_()` |
| Modify | `app/templates/login.html` | Replace hardcoded strings with `_()`, add language selector |
| Modify | `app/templates/register.html` | Replace hardcoded strings with `_()`, add language selector |
| Modify | `app/templates/choose_username.html` | Replace hardcoded strings with `_()`, add language selector |
| Modify | `tests/conftest.py` | Add `language` column to test schema |

---

### Task 1: Create i18n module with translation files

**Files:**
- Create: `app/i18n/__init__.py`
- Create: `app/i18n/pt.json`
- Create: `app/i18n/en.json`
- Create: `app/i18n/es.json`
- Test: `tests/test_i18n.py`

- [ ] **Step 1: Write failing tests for the i18n module**

Create `tests/test_i18n.py`:

```python
from app.i18n import translate, SUPPORTED_LANGS


def test_translate_returns_portuguese_string():
    assert translate("header.profile", "pt") == "Meu Perfil"


def test_translate_returns_english_string():
    assert translate("header.profile", "en") == "My Profile"


def test_translate_returns_spanish_string():
    assert translate("header.profile", "es") == "Mi Perfil"


def test_translate_falls_back_to_pt_for_missing_key():
    # A key that exists only in pt.json
    result = translate("header.profile", "xx")
    assert result == "Meu Perfil"


def test_translate_returns_key_when_not_found_anywhere():
    assert translate("nonexistent.key", "en") == "nonexistent.key"


def test_supported_langs():
    assert SUPPORTED_LANGS == {"en", "pt", "es"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_i18n.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.i18n'`

- [ ] **Step 3: Create the Portuguese translation file**

Create `app/i18n/pt.json`:

```json
{
  "header.profile": "Meu Perfil",
  "header.settings": "Configurações",
  "header.theme": "Tema",
  "header.language": "Idioma",
  "header.logout": "Sair",
  "header.light": "Claro",
  "header.dark": "Escuro",
  "header.auto": "Auto",
  "home.subjects": "Assuntos",
  "home.new_subject": "Novo Assunto",
  "home.rename": "Renomear",
  "home.change_image": "Trocar imagem",
  "home.delete": "Excluir",
  "topics.topics": "Tópicos",
  "topics.library": "Biblioteca",
  "topics.add_content": "Adicionar conteúdo",
  "topics.close_chat": "Fechar chat",
  "topics.close_library": "Fechar biblioteca",
  "topics.chat_placeholder": "Digite sua pergunta...",
  "topics.chat_greeting": "Olá! Sou seu assistente de estudos. Pergunte qualquer coisa sobre este assunto.",
  "topics.chat_about": "Conversar sobre o assunto",
  "topics.reload": "Recarregar",
  "topics.delete": "Excluir",
  "login.page_title": "Entrar — resumiu",
  "login.title": "Entre na sua conta",
  "login.email": "Email",
  "login.password": "Senha",
  "login.submit": "Entrar",
  "login.or_continue": "ou continue com",
  "login.no_account": "Não tem conta?",
  "login.create_account": "Criar conta",
  "login.invalid_credentials": "Email ou senha incorretos.",
  "login.oauth_email_error": "Não foi possível obter o email do provedor.",
  "register.page_title": "Criar Conta — resumiu",
  "register.title": "Crie sua conta",
  "register.username": "Username",
  "register.username_hint": "Apenas letras minúsculas, números e hífens",
  "register.email": "Email",
  "register.password": "Senha",
  "register.confirm_password": "Confirmar senha",
  "register.submit": "Criar conta",
  "register.or_continue": "ou continue com",
  "register.has_account": "Já tem conta?",
  "register.sign_in": "Entrar",
  "register.passwords_mismatch": "As senhas não coincidem.",
  "register.email_or_username_taken": "Email ou username já em uso.",
  "choose_username.page_title": "Escolha seu Username — resumiu",
  "choose_username.title": "Escolha seu username",
  "choose_username.submit": "Continuar",
  "choose_username.username_taken": "Username já em uso.",
  "validation.username_min": "Username deve ter pelo menos 2 caracteres.",
  "validation.username_max": "Username deve ter no máximo 40 caracteres.",
  "validation.username_pattern": "Username deve conter apenas letras minúsculas, números e hífens, e começar com letra ou número."
}
```

- [ ] **Step 4: Create the English translation file**

Create `app/i18n/en.json`:

```json
{
  "header.profile": "My Profile",
  "header.settings": "Settings",
  "header.theme": "Theme",
  "header.language": "Language",
  "header.logout": "Sign out",
  "header.light": "Light",
  "header.dark": "Dark",
  "header.auto": "Auto",
  "home.subjects": "Subjects",
  "home.new_subject": "New Subject",
  "home.rename": "Rename",
  "home.change_image": "Change image",
  "home.delete": "Delete",
  "topics.topics": "Topics",
  "topics.library": "Library",
  "topics.add_content": "Add content",
  "topics.close_chat": "Close chat",
  "topics.close_library": "Close library",
  "topics.chat_placeholder": "Ask a question...",
  "topics.chat_greeting": "Hello! I'm your study assistant. Ask me anything about this subject.",
  "topics.chat_about": "Chat about this subject",
  "topics.reload": "Reload",
  "topics.delete": "Delete",
  "login.page_title": "Sign In — resumiu",
  "login.title": "Sign in to your account",
  "login.email": "Email",
  "login.password": "Password",
  "login.submit": "Sign in",
  "login.or_continue": "or continue with",
  "login.no_account": "Don't have an account?",
  "login.create_account": "Create account",
  "login.invalid_credentials": "Invalid email or password.",
  "login.oauth_email_error": "Could not get email from provider.",
  "register.page_title": "Create Account — resumiu",
  "register.title": "Create your account",
  "register.username": "Username",
  "register.username_hint": "Lowercase letters, numbers, and hyphens only",
  "register.email": "Email",
  "register.password": "Password",
  "register.confirm_password": "Confirm password",
  "register.submit": "Create account",
  "register.or_continue": "or continue with",
  "register.has_account": "Already have an account?",
  "register.sign_in": "Sign in",
  "register.passwords_mismatch": "Passwords don't match.",
  "register.email_or_username_taken": "Email or username already in use.",
  "choose_username.page_title": "Choose Username — resumiu",
  "choose_username.title": "Choose your username",
  "choose_username.submit": "Continue",
  "choose_username.username_taken": "Username already in use.",
  "validation.username_min": "Username must be at least 2 characters.",
  "validation.username_max": "Username must be at most 40 characters.",
  "validation.username_pattern": "Username must contain only lowercase letters, numbers, and hyphens, and start with a letter or number."
}
```

- [ ] **Step 5: Create the Spanish translation file**

Create `app/i18n/es.json`:

```json
{
  "header.profile": "Mi Perfil",
  "header.settings": "Configuración",
  "header.theme": "Tema",
  "header.language": "Idioma",
  "header.logout": "Salir",
  "header.light": "Claro",
  "header.dark": "Oscuro",
  "header.auto": "Auto",
  "home.subjects": "Asignaturas",
  "home.new_subject": "Nueva Asignatura",
  "home.rename": "Renombrar",
  "home.change_image": "Cambiar imagen",
  "home.delete": "Eliminar",
  "topics.topics": "Temas",
  "topics.library": "Biblioteca",
  "topics.add_content": "Agregar contenido",
  "topics.close_chat": "Cerrar chat",
  "topics.close_library": "Cerrar biblioteca",
  "topics.chat_placeholder": "Escribe tu pregunta...",
  "topics.chat_greeting": "¡Hola! Soy tu asistente de estudios. Pregúntame cualquier cosa sobre este tema.",
  "topics.chat_about": "Conversar sobre el tema",
  "topics.reload": "Recargar",
  "topics.delete": "Eliminar",
  "login.page_title": "Iniciar Sesión — resumiu",
  "login.title": "Inicia sesión en tu cuenta",
  "login.email": "Email",
  "login.password": "Contraseña",
  "login.submit": "Iniciar sesión",
  "login.or_continue": "o continúa con",
  "login.no_account": "¿No tienes cuenta?",
  "login.create_account": "Crear cuenta",
  "login.invalid_credentials": "Email o contraseña incorrectos.",
  "login.oauth_email_error": "No se pudo obtener el email del proveedor.",
  "register.page_title": "Crear Cuenta — resumiu",
  "register.title": "Crea tu cuenta",
  "register.username": "Username",
  "register.username_hint": "Solo letras minúsculas, números y guiones",
  "register.email": "Email",
  "register.password": "Contraseña",
  "register.confirm_password": "Confirmar contraseña",
  "register.submit": "Crear cuenta",
  "register.or_continue": "o continúa con",
  "register.has_account": "¿Ya tienes cuenta?",
  "register.sign_in": "Iniciar sesión",
  "register.passwords_mismatch": "Las contraseñas no coinciden.",
  "register.email_or_username_taken": "Email o username ya en uso.",
  "choose_username.page_title": "Elige tu Username — resumiu",
  "choose_username.title": "Elige tu username",
  "choose_username.submit": "Continuar",
  "choose_username.username_taken": "Username ya en uso.",
  "validation.username_min": "El username debe tener al menos 2 caracteres.",
  "validation.username_max": "El username debe tener como máximo 40 caracteres.",
  "validation.username_pattern": "El username solo puede contener letras minúsculas, números y guiones, y debe comenzar con letra o número."
}
```

- [ ] **Step 6: Create the i18n module**

Create `app/i18n/__init__.py`:

```python
import json
from pathlib import Path

SUPPORTED_LANGS = {"en", "pt", "es"}
_DEFAULT_LANG = "pt"

_translations: dict[str, dict[str, str]] = {}

_dir = Path(__file__).parent
for lang in SUPPORTED_LANGS:
    path = _dir / f"{lang}.json"
    with open(path, encoding="utf-8") as f:
        _translations[lang] = json.load(f)


def translate(key: str, lang: str) -> str:
    """Look up a translation key. Falls back to pt, then returns the key itself."""
    if lang in _translations:
        value = _translations[lang].get(key)
        if value is not None:
            return value
    # Fallback to Portuguese
    if lang != _DEFAULT_LANG:
        value = _translations[_DEFAULT_LANG].get(key)
        if value is not None:
            return value
    return key
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_i18n.py -v`
Expected: All 6 tests PASS

- [ ] **Step 8: Commit**

```bash
git add app/i18n/__init__.py app/i18n/pt.json app/i18n/en.json app/i18n/es.json tests/test_i18n.py
git commit -m "feat: add i18n module with EN/PT/ES translation files"
```

---

### Task 2: Create language resolution middleware

**Files:**
- Create: `app/i18n/middleware.py`
- Test: `tests/test_i18n.py` (append)

- [ ] **Step 1: Write failing tests for the middleware**

Append to `tests/test_i18n.py`:

```python
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
    # Should not redirect, just ignore invalid lang
    assert resp.status_code == 200
    assert resp.text == "pt"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_i18n.py::test_middleware_defaults_to_pt -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.i18n.middleware'`

- [ ] **Step 3: Implement the middleware**

Create `app/i18n/middleware.py`:

```python
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.i18n import SUPPORTED_LANGS

_DEFAULT_LANG = "pt"


def _parse_accept_language(header: str) -> str | None:
    """Parse Accept-Language header, return best supported language or None."""
    parts = []
    for item in header.split(","):
        item = item.strip()
        if ";q=" in item:
            lang, q = item.split(";q=")
            parts.append((lang.strip(), float(q)))
        else:
            parts.append((item, 1.0))
    parts.sort(key=lambda x: x[1], reverse=True)
    for lang, _ in parts:
        # Match "en-US" -> "en", "pt-BR" -> "pt", etc.
        short = lang.split("-")[0].lower()
        if short in SUPPORTED_LANGS:
            return short
    return None


class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        lang = None

        # 1. Query param ?lang=xx
        query_lang = request.query_params.get("lang")
        if query_lang and query_lang in SUPPORTED_LANGS:
            # Set cookie and redirect without the query param
            parsed = urlparse(str(request.url))
            params = parse_qs(parsed.query)
            params.pop("lang", None)
            clean_query = urlencode(params, doseq=True)
            clean_url = urlunparse(parsed._replace(query=clean_query))
            response = RedirectResponse(clean_url, status_code=307)
            response.set_cookie("lang", query_lang, max_age=365 * 86400, samesite="lax")
            return response

        # 2. Cookie
        cookie_lang = request.cookies.get("lang")
        if cookie_lang and cookie_lang in SUPPORTED_LANGS:
            lang = cookie_lang

        # 3. Accept-Language header
        if not lang:
            accept = request.headers.get("accept-language", "")
            if accept:
                lang = _parse_accept_language(accept)

        # 4. Fallback
        request.state.lang = lang or _DEFAULT_LANG
        response = await call_next(request)
        return response
```

Note: Step 3 in the spec (user DB preference) is checked in `get_current_user` rather than the middleware, because the middleware does not have access to the DB dependency. The user's DB preference will override the cookie/accept-language when injected in Task 4.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_i18n.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/i18n/middleware.py tests/test_i18n.py
git commit -m "feat: add language resolution middleware"
```

---

### Task 3: Database migration and auth integration

**Files:**
- Create: `db/migrations/YYYYMMDDHHMMSS_add_language_to_users.sql` (use `make db-new name=add_language_to_users`)
- Modify: `app/auth.py:23-31` — use translation keys for validate_username
- Modify: `app/auth.py:55-69` — include `language` in user dict
- Modify: `tests/conftest.py` — add `language` column to test schema

- [ ] **Step 1: Create the migration**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make db-new name=add_language_to_users`

Then edit the generated file to contain:

```sql
-- migrate:up
ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'pt';

-- migrate:down
ALTER TABLE users DROP COLUMN language;
```

- [ ] **Step 2: Run the migration**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make migrate`
Expected: Migration applied successfully

- [ ] **Step 3: Update test schema in conftest.py**

In `tests/conftest.py`, update the `users` table in the `SCHEMA` string to add the `language` column:

```python
# In the SCHEMA string, change the users table to:
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    language TEXT NOT NULL DEFAULT 'pt',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

- [ ] **Step 4: Update `get_current_user` in auth.py to include language**

In `app/auth.py`, modify `get_current_user` (lines 55-69):

Change the SQL query from:
```python
    row = await db.execute(
        """SELECT u.id, u.username, u.email
           FROM sessions s JOIN users u ON s.user_id = u.id
           WHERE s.token = ? AND s.expires_at > ?""",
        (token, datetime.now(timezone.utc).isoformat()),
    )
```
to:
```python
    row = await db.execute(
        """SELECT u.id, u.username, u.email, u.language
           FROM sessions s JOIN users u ON s.user_id = u.id
           WHERE s.token = ? AND s.expires_at > ?""",
        (token, datetime.now(timezone.utc).isoformat()),
    )
```

And change the return dict from:
```python
    return {"id": user["id"], "username": user["username"], "email": user["email"],
            "name": user["username"], "initials": user["username"][:2].upper()}
```
to:
```python
    return {"id": user["id"], "username": user["username"], "email": user["email"],
            "name": user["username"], "initials": user["username"][:2].upper(),
            "language": user["language"]}
```

- [ ] **Step 5: Update `validate_username` to return translation keys**

In `app/auth.py`, change `validate_username` (lines 23-31) from:

```python
def validate_username(username: str) -> str | None:
    """Return error message or None if valid."""
    if not username or len(username) < 2:
        return "Username deve ter pelo menos 2 caracteres."
    if len(username) > 40:
        return "Username deve ter no máximo 40 caracteres."
    if not USERNAME_PATTERN.match(username):
        return "Username deve conter apenas letras minúsculas, números e hífens, e começar com letra ou número."
    return None
```

to:

```python
def validate_username(username: str) -> str | None:
    """Return i18n key or None if valid."""
    if not username or len(username) < 2:
        return "validation.username_min"
    if len(username) > 40:
        return "validation.username_max"
    if not USERNAME_PATTERN.match(username):
        return "validation.username_pattern"
    return None
```

- [ ] **Step 6: Run existing tests to check nothing is broken**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: Some test_auth tests may fail because they assert on the old Portuguese error strings. If so, update those assertions in the next step.

- [ ] **Step 7: Fix any broken test assertions**

If tests assert old Portuguese strings from `validate_username`, update them to check for the i18n keys instead. The rendered template will show the translated string (once templates are updated), but the `validate_username` function now returns keys.

However, since the templates currently render `{{ error }}` directly, the error will temporarily show as the translation key until templates are updated in Task 6. This is acceptable as an intermediate state — the translated rendering happens when `_()` is integrated.

- [ ] **Step 8: Commit**

```bash
git add db/migrations/*add_language_to_users* app/auth.py tests/conftest.py
git commit -m "feat: add language column to users, return i18n keys from validate_username"
```

---

### Task 4: Register middleware and Jinja2 global in main.py

**Files:**
- Modify: `app/main.py` — register middleware, register `_()` global, add `/htmx/set-language` route
- Test: `tests/test_i18n.py` (append)

- [ ] **Step 1: Write failing test for the set-language route**

Append to `tests/test_i18n.py`:

```python
from tests.conftest import auth_client


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_i18n.py::test_set_language_saves_cookie_and_refreshes -v`
Expected: FAIL with 404 (route not found)

- [ ] **Step 3: Register middleware and Jinja2 global in main.py**

In `app/main.py`, add imports after the existing imports (after line 24):

```python
from app.i18n import translate, SUPPORTED_LANGS
from app.i18n.middleware import LanguageMiddleware
```

Add middleware registration after the SessionMiddleware (after line 31):

```python
app.add_middleware(LanguageMiddleware)
```

Register the Jinja2 global right after the `templates = Jinja2Templates(...)` line (after line 35). This makes `_()` available in all templates, using the language from the current request:

```python
def _make_jinja_translate(request: Request):
    lang = getattr(request.state, "lang", "pt")
    return lambda key: translate(key, lang)
```

We need a context processor approach. Since Jinja2Templates doesn't support global functions that read request state directly, we'll add `_` to each template context. Add a helper after the `templates` line:

```python
_original_template_response = templates.TemplateResponse

def _i18n_template_response(request, *args, **kwargs):
    context = kwargs.get("context", {})
    if "context" not in kwargs and len(args) >= 2:
        # positional: name, context
        pass
    lang = getattr(request.state, "lang", "pt")
    # If user is logged in, prefer their DB language over middleware resolution
    user = context.get("user")
    if user and user.get("language"):
        lang = user["language"]
    context["_"] = lambda key: translate(key, lang)
    context["current_lang"] = lang
    kwargs["context"] = context
    return _original_template_response(request=request, *args, **kwargs)

templates.TemplateResponse = _i18n_template_response
```

Actually, a cleaner approach — since every `TemplateResponse` call already passes `request=request` and `context=`, we can monkey-patch it simply. But the cleanest FastAPI approach is to just ensure `_` and `current_lang` are in every context dict. Let's instead create a simple helper function:

```python
def _ctx(request: Request, context: dict | None = None) -> dict:
    """Add i18n helpers to template context."""
    ctx = context or {}
    lang = getattr(request.state, "lang", "pt")
    user = ctx.get("user")
    if user and user.get("language"):
        lang = user["language"]
    ctx["_"] = lambda key: translate(key, lang)
    ctx["current_lang"] = lang
    return ctx
```

Then update every `TemplateResponse` call to wrap context with `_ctx()`. For example:

```python
# Before:
return templates.TemplateResponse(request=request, name="login.html", context={})
# After:
return templates.TemplateResponse(request=request, name="login.html", context=_ctx(request))

# Before:
return templates.TemplateResponse(request=request, name="login.html", context={"error": "..."})
# After:
return templates.TemplateResponse(request=request, name="login.html", context=_ctx(request, {"error": "..."}))
```

Update ALL `TemplateResponse` calls in `main.py`. The complete list:

1. `login_page` (line 60): `context=_ctx(request)`
2. `login_submit` error (line 73-77): `context=_ctx(request, {"error": translate("login.invalid_credentials", request.state.lang)})`
3. `register_page` (line 86): `context=_ctx(request)`
4. `register_submit` validation error (line 101-105): `context=_ctx(request, {"error": translate(err, request.state.lang), "username": username, "email": email})`
5. `register_submit` password mismatch (line 107-110): `context=_ctx(request, {"error": translate("register.passwords_mismatch", request.state.lang), "username": username, "email": email})`
6. `register_submit` duplicate (line 114-117): `context=_ctx(request, {"error": translate("register.email_or_username_taken", request.state.lang), "username": username, "email": email})`
7. `choose_username_page` (line 146): `context=_ctx(request)`
8. `choose_username_submit` validation error (line 161-165): `context=_ctx(request, {"error": translate(err, request.state.lang), "username": username})`
9. `choose_username_submit` taken (line 169-172): `context=_ctx(request, {"error": translate("choose_username.username_taken", request.state.lang), "username": username})`
10. `user_subjects` (line 289-292): `context=_ctx(request, {"user": user, "subjects": subjects})`
11. `subject_topics` (line 330-341): `context=_ctx(request, {"user": user, "subject": subject, ...})`
12. `htmx_detail` (line 378-381): `context=_ctx(request, {"detail": {"content_html": content_html}})`
13. `oauth_callback` email error (line 233-237): `context=_ctx(request, {"error": translate("login.oauth_email_error", request.state.lang)})`
14. `htmx_hello` (line 389): no context needed, but for consistency: `context=_ctx(request)`

- [ ] **Step 4: Add the `/htmx/set-language` route**

Add this route to `app/main.py` near the bottom, before `htmx_hello`:

```python
@app.post("/htmx/set-language")
async def htmx_set_language(
    request: Request,
    lang: str = Form(...),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    if lang not in SUPPORTED_LANGS:
        return Response(status_code=400)
    await db.execute("UPDATE users SET language = ? WHERE id = ?", (lang, user["id"]))
    await db.commit()
    response = Response(status_code=200)
    response.headers["HX-Refresh"] = "true"
    response.set_cookie("lang", lang, max_age=365 * 86400, samesite="lax")
    return response
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_i18n.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run full test suite**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS (existing tests should still work since `_ctx` adds `_` and `current_lang` to context, which templates haven't used yet)

- [ ] **Step 7: Commit**

```bash
git add app/main.py tests/test_i18n.py
git commit -m "feat: register i18n middleware, Jinja2 context helper, set-language route"
```

---

### Task 5: Create language selector partial and update base.html

**Files:**
- Create: `app/templates/partials/language_selector.html`
- Modify: `app/templates/base.html:2`

- [ ] **Step 1: Create the language selector partial**

Create `app/templates/partials/language_selector.html`:

```html
{# Language selector — inline flag buttons.
   Requires `current_lang` in template context.
   mode: "menu" (HTMX POST for logged-in users) or "public" (query param links).
   Pass mode via: {% include "partials/language_selector.html" with context %}
   and set `lang_mode` before including. #}
{% set flags = [("en", "🇺🇸"), ("pt", "🇧🇷"), ("es", "🇪🇸")] %}
<div class="flex items-center gap-1">
  {% for code, flag in flags %}
  {% if lang_mode == "menu" %}
  <button
    hx-post="/htmx/set-language"
    hx-vals='{"lang": "{{ code }}"}'
    class="w-8 h-8 flex items-center justify-center rounded-lg text-base transition-colors cursor-pointer
      {% if current_lang == code %}bg-indigo-500/20 ring-1 ring-indigo-400{% else %}hover:bg-slate-100 dark:hover:bg-neutral-700{% endif %}"
  >{{ flag }}</button>
  {% else %}
  <a
    href="?lang={{ code }}"
    class="w-8 h-8 flex items-center justify-center rounded-lg text-base transition-colors
      {% if current_lang == code %}bg-indigo-500/20 ring-1 ring-indigo-400{% else %}hover:bg-slate-100 dark:hover:bg-neutral-700{% endif %}"
  >{{ flag }}</a>
  {% endif %}
  {% endfor %}
</div>
```

- [ ] **Step 2: Update base.html lang attribute**

In `app/templates/base.html`, change line 2 from:

```html
<html lang="pt-BR" x-data="themeManager()" :class="{ 'dark': isDark }">
```

to:

```html
<html lang="{{ current_lang | default('pt') }}" x-data="themeManager()" :class="{ 'dark': isDark }">
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/language_selector.html app/templates/base.html
git commit -m "feat: add language selector partial and dynamic html lang attribute"
```

---

### Task 6: Update header.html with i18n and language selector

**Files:**
- Modify: `app/templates/partials/header.html`

- [ ] **Step 1: Replace all hardcoded strings and add language selector**

Replace the full content of `app/templates/partials/header.html`. The changes are:

1. Replace `Meu Perfil` with `{{ _('header.profile') }}`
2. Replace `Configurações` with `{{ _('header.settings') }}`
3. Replace `Tema` with `{{ _('header.theme') }}`
4. Replace `Claro` with `{{ _('header.light') }}`
5. Replace `Escuro` with `{{ _('header.dark') }}`
6. Replace `Auto` with `{{ _('header.auto') }}`
7. Replace `Sair` with `{{ _('header.logout') }}`
8. Add language selector section between theme and logout divider

The language selector section to insert (after the theme toggle `</div>` and before the logout divider `<div class="border-t ...">`) is:

```html
            <!-- Language selector -->
            <div class="flex items-center justify-between px-4 py-2.5">
              <span class="flex items-center gap-2.5 text-sm text-slate-700 dark:text-neutral-300">
                <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
                </svg>
                {{ _('header.language') }}
              </span>
              {% set lang_mode = "menu" %}
              {% include "partials/language_selector.html" %}
            </div>
```

- [ ] **Step 2: Run existing tests to verify nothing is broken**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS (the `_` function is now in the context from Task 4)

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/header.html
git commit -m "feat: i18n header menu strings and language selector"
```

---

### Task 7: Update login.html with i18n

**Files:**
- Modify: `app/templates/login.html`

- [ ] **Step 1: Replace all hardcoded strings and add language selector**

In `app/templates/login.html`:

1. Line 2: `{% block title %}{{ _('login.page_title') }}{% endblock %}`
2. Line 11: `<p ...>{{ _('login.title') }}</p>`
3. Line 21: `placeholder="{{ _('login.email') }}"`
4. Line 23: `placeholder="{{ _('login.password') }}"`
5. Line 26: button text `{{ _('login.submit') }}`
6. Line 34: `<span ...>{{ _('login.or_continue') }}</span>`
7. Line 53: `{{ _('login.no_account') }}`
8. Line 54: `<a ...>{{ _('login.create_account') }}</a>`

Add language selector after the opening `<div class="w-full max-w-sm">` (after line 5), before the logo section:

```html
    <!-- Language selector -->
    <div class="flex justify-end mb-4">
      {% set lang_mode = "public" %}
      {% include "partials/language_selector.html" %}
    </div>
```

- [ ] **Step 2: Write a test to verify login page renders in English**

Append to `tests/test_i18n.py`:

```python
def test_login_page_renders_in_english(auth_client):
    # Use a fresh client without auth to hit login page
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    resp = client.get("/login", cookies={"lang": "en"})
    assert resp.status_code == 200
    assert "Sign in to your account" in resp.text
    assert "Entre na sua conta" not in resp.text
```

- [ ] **Step 3: Run tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_i18n.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add app/templates/login.html tests/test_i18n.py
git commit -m "feat: i18n login page strings and language selector"
```

---

### Task 8: Update register.html with i18n

**Files:**
- Modify: `app/templates/register.html`

- [ ] **Step 1: Replace all hardcoded strings and add language selector**

In `app/templates/register.html`:

1. Line 2: `{% block title %}{{ _('register.page_title') }}{% endblock %}`
2. Line 10: `<p ...>{{ _('register.title') }}</p>`
3. Line 19: `placeholder="{{ _('register.username') }}"` and hint `{{ _('register.username_hint') }}`
4. Line 23: `placeholder="{{ _('register.email') }}"`
5. Line 25: `placeholder="{{ _('register.password') }}"`
6. Line 27: `placeholder="{{ _('register.confirm_password') }}"`
7. Line 30: button text `{{ _('register.submit') }}`
8. Line 37: `<span ...>{{ _('register.or_continue') }}</span>`
9. Line 53: `{{ _('register.has_account') }}`
10. Line 54: `<a ...>{{ _('register.sign_in') }}</a>`

Add language selector the same way as login.html — after `<div class="w-full max-w-sm">`:

```html
    <div class="flex justify-end mb-4">
      {% set lang_mode = "public" %}
      {% include "partials/language_selector.html" %}
    </div>
```

- [ ] **Step 2: Run tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add app/templates/register.html
git commit -m "feat: i18n register page strings and language selector"
```

---

### Task 9: Update choose_username.html with i18n

**Files:**
- Modify: `app/templates/choose_username.html`

- [ ] **Step 1: Replace all hardcoded strings and add language selector**

In `app/templates/choose_username.html`:

1. Line 2: `{% block title %}{{ _('choose_username.page_title') }}{% endblock %}`
2. Line 9: `<p ...>{{ _('choose_username.title') }}</p>`
3. Line 19: hint text `{{ _('register.username_hint') }}`
4. Line 22: button text `{{ _('choose_username.submit') }}`

Add language selector after `<div class="w-full max-w-sm">`:

```html
    <div class="flex justify-end mb-4">
      {% set lang_mode = "public" %}
      {% include "partials/language_selector.html" %}
    </div>
```

- [ ] **Step 2: Run tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add app/templates/choose_username.html
git commit -m "feat: i18n choose-username page strings and language selector"
```

---

### Task 10: Update home.html with i18n

**Files:**
- Modify: `app/templates/home.html`

- [ ] **Step 1: Replace all hardcoded strings**

In `app/templates/home.html`:

1. Line 7: `<h1 ...>{{ _('home.subjects') }}</h1>`
2. Line 12: `<span ...>{{ _('home.new_subject') }}</span>`
3. Line 61: `Renomear` → `{{ _('home.rename') }}`
4. Line 67: `Trocar imagem` → `{{ _('home.change_image') }}`
5. Line 73: `Excluir` → `{{ _('home.delete') }}`

- [ ] **Step 2: Write a test to verify home renders with translated strings**

Append to `tests/test_i18n.py`:

```python
def test_home_page_renders_in_english(auth_client):
    # Set user language to English in DB
    import asyncio, aiosqlite
    # The auth_client fixture uses testuser, so update language directly
    resp = auth_client.post("/htmx/set-language", data={"lang": "en"})
    assert resp.status_code == 200
    # Now fetch the home page
    resp = auth_client.get("/testuser")
    assert resp.status_code == 200
    assert "Subjects" in resp.text
```

- [ ] **Step 3: Run tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_i18n.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add app/templates/home.html tests/test_i18n.py
git commit -m "feat: i18n home page strings"
```

---

### Task 11: Update topics.html with i18n

**Files:**
- Modify: `app/templates/topics.html`

- [ ] **Step 1: Replace all hardcoded strings**

In `app/templates/topics.html`:

1. Line 10: `chatMessages = [{ role: 'assistant', text: '{{ _("topics.chat_greeting") }}' }]` (escape single quotes if needed — the English string uses `I'm` which contains a quote; use the Jinja2 output in a JS-safe way: `{{ _("topics.chat_greeting") | e }}`)

   Actually, since Alpine.js `x-init` uses single quotes for the JS string, we need to handle this carefully. Change to:
   ```html
   x-init="chatMessages = [{ role: 'assistant', text: {{ _('topics.chat_greeting') | tojson }} }]"
   ```
   The `tojson` filter outputs a properly escaped JSON string (with quotes).

2. Line 25: `title="Fechar chat"` → `title="{{ _('topics.close_chat') }}"`
3. Line 61: `placeholder="Digite sua pergunta..."` → `placeholder="{{ _('topics.chat_placeholder') }}"`
4. Line 87: `title="Adicionar conteúdo"` �� `title="{{ _('topics.add_content') }}"`
5. Line 92: `<h2 ...>Biblioteca</h2>` ��� `<h2 ...>{{ _('topics.library') }}</h2>`
6. Line 93: `title="Fechar biblioteca"` → `title="{{ _('topics.close_library') }}"`
7. Line 146: `Recarregar` → `{{ _('topics.reload') }}`
8. Line 151: `Excluir` → `{{ _('topics.delete') }}`
9. Line 167: `<h1 ...>Tópicos</h1>` → `<h1 ...>{{ _('topics.topics') }}</h1>`
10. Line 178: `<span ...>Biblioteca</span>` → `<span ...>{{ _('topics.library') }}</span>`
11. Line 189: `<span ...>Conversar sobre o assunto</span>` → `<span ...>{{ _('topics.chat_about') }}</span>`
12. Line 183: `title="Conversar sobre o assunto"` → `title="{{ _('topics.chat_about') }}"`
13. Line 172: `title="Abrir biblioteca"` → `title="{{ _('topics.library') }}"`

- [ ] **Step 2: Run tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: i18n topics page strings"
```

---

### Task 12: Save user language on registration

**Files:**
- Modify: `app/main.py` — update `register_submit` and `choose_username_submit` to save language

- [ ] **Step 1: Update register_submit to save language preference**

In `app/main.py`, in the `register_submit` function, change the INSERT query from:

```python
    cursor = await db.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, hash_password(password)),
    )
```

to:

```python
    lang = getattr(request.state, "lang", "pt")
    cursor = await db.execute(
        "INSERT INTO users (username, email, password_hash, language) VALUES (?, ?, ?, ?)",
        (username, email, hash_password(password), lang),
    )
```

- [ ] **Step 2: Update choose_username_submit to save language preference**

In `app/main.py`, in `choose_username_submit`, change:

```python
    cursor = await db.execute(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        (username, email),
    )
```

to:

```python
    lang = getattr(request.state, "lang", "pt")
    cursor = await db.execute(
        "INSERT INTO users (username, email, language) VALUES (?, ?, ?)",
        (username, email, lang),
    )
```

- [ ] **Step 3: Run full test suite**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: save detected language on user registration"
```

---

### Task 13: Final integration test

**Files:**
- Test: `tests/test_i18n.py` (append)

- [ ] **Step 1: Write an end-to-end language switching test**

Append to `tests/test_i18n.py`:

```python
def test_language_switch_persists_to_db(auth_client):
    """Full flow: switch language, verify it persists across requests."""
    # Switch to Spanish
    resp = auth_client.post("/htmx/set-language", data={"lang": "es"})
    assert resp.status_code == 200
    assert resp.headers.get("HX-Refresh") == "true"

    # Verify home page now shows Spanish strings
    resp = auth_client.get("/testuser")
    assert resp.status_code == 200
    assert "Asignaturas" in resp.text


def test_public_page_language_via_cookie():
    """Public pages respect the lang cookie."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    # Set cookie via query param redirect
    resp = client.get("/login?lang=es", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.cookies.get("lang") == "es"

    # Follow up — now use the cookie
    client.cookies.set("lang", "es")
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Inicia sesión en tu cuenta" in resp.text
```

- [ ] **Step 2: Run all tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_i18n.py
git commit -m "test: add end-to-end i18n integration tests"
```

---

### Task 14: Manual verification

- [ ] **Step 1: Start the dev server**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`

- [ ] **Step 2: Test in browser**

1. Open `http://localhost:8000/login`
2. Verify Portuguese strings are shown by default
3. Click the 🇺🇸 flag — page should reload with English strings
4. Click the 🇪🇸 flag — page should reload with Spanish strings
5. Log in and verify the menu shows the language selector with flags
6. Switch language in the menu — verify it persists
7. Navigate to a subject's topics page — verify translated strings
8. Log out and back in — verify language preference persisted

- [ ] **Step 3: Final commit (if any fixes needed)**

Fix any issues found during manual testing and commit.
