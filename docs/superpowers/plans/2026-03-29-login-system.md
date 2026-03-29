# Login System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add email/password authentication, OAuth2 social login (Google, GitHub, Microsoft), and session management to the easy-boiler app.

**Architecture:** Server-side sessions stored in SQLite via aiosqlite. Auth logic isolated in `app/auth.py`. OAuth2 via authlib. Password hashing via passlib/bcrypt. Protected routes redirect to `/login`. Templates follow existing fullscreen minimalista style with Tailwind + Alpine.js.

**Tech Stack:** FastAPI, aiosqlite, authlib, passlib[bcrypt], Jinja2, Tailwind CSS, Alpine.js, HTMX

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `db/migrations/20260329000000_create_auth_tables.sql` | create | users, sessions, oauth_accounts tables |
| `app/auth.py` | create | Password hashing, session CRUD, get_current_user/require_auth dependencies, OAuth client config |
| `app/main.py` | modify | Add auth routes, protect existing routes, remove MOCK_USER from protected routes |
| `app/templates/login.html` | create | Login page |
| `app/templates/register.html` | create | Registration page |
| `app/templates/choose_username.html` | create | Post-OAuth username selection |
| `app/templates/partials/header.html` | modify | Use real user data from session |
| `.env.example` | modify | Add SECRET_KEY and OAuth env vars |
| `pyproject.toml` | modify | Add authlib, passlib[bcrypt] |
| `tests/test_auth.py` | create | Auth tests |

---

### Task 1: Database Migration

**Files:**
- Create: `db/migrations/20260329000000_create_auth_tables.sql`

- [ ] **Step 1: Create migration file**

```sql
-- migrate:up
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT     NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_token ON sessions(token);

CREATE TABLE oauth_accounts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider         TEXT    NOT NULL,
    provider_user_id TEXT    NOT NULL,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);

-- migrate:down
DROP TABLE IF EXISTS oauth_accounts;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS users;
```

- [ ] **Step 2: Run migration**

Run: `make migrate`
Expected: Migration applies successfully, `db/schema.sql` updated with new tables.

- [ ] **Step 3: Commit**

```bash
git add db/migrations/20260329000000_create_auth_tables.sql db/schema.sql
git commit -m "feat: add auth tables migration (users, sessions, oauth_accounts)"
```

---

### Task 2: Dependencies and Environment

**Files:**
- Modify: `pyproject.toml:6-15`
- Modify: `.env.example`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Add `authlib` and `passlib[bcrypt]` to the `dependencies` list in `pyproject.toml`:

```toml
dependencies = [
    "aiosqlite",
    "authlib",
    "fastapi",
    "jinja2",
    "markdown",
    "passlib[bcrypt]",
    "python-dotenv",
    "yt-dlp",
    "uvicorn[standard]",
    "youtube-transcript-api",
]
```

- [ ] **Step 2: Add env vars to .env.example**

Append to `.env.example`:

```
# Auth
SECRET_KEY=change-me-to-a-random-string

# OAuth (leave empty to disable a provider)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
```

- [ ] **Step 3: Sync dependencies**

Run: `uv sync`
Expected: authlib and passlib[bcrypt] installed successfully.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .env.example uv.lock
git commit -m "feat: add auth dependencies (authlib, passlib) and env vars"
```

---

### Task 3: Auth Module — Password Hashing and Session Management

**Files:**
- Create: `app/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests for password hashing**

Create `tests/test_auth.py`:

```python
import pytest
from app.auth import hash_password, verify_password


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("mypassword")
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("mypassword")
    assert verify_password("wrongpassword", hashed) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth'`

- [ ] **Step 3: Implement password hashing in app/auth.py**

Create `app/auth.py`:

```python
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_COOKIE = "session_token"
SESSION_MAX_AGE_DAYS = 30
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def validate_username(username: str) -> str | None:
    """Return error message or None if valid."""
    if not username or len(username) < 2:
        return "Username deve ter pelo menos 2 caracteres."
    if len(username) > 40:
        return "Username deve ter no máximo 40 caracteres."
    if not USERNAME_PATTERN.match(username):
        return "Username deve conter apenas letras minúsculas, números e hífens, e começar com letra ou número."
    return None


async def create_session(db, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_MAX_AGE_DAYS)
    await db.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires_at.isoformat()),
    )
    await db.commit()
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE_DAYS * 86400,
        httponly=True,
        samesite="lax",
    )


async def get_current_user(request: Request, db) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = await db.execute(
        """SELECT u.id, u.username, u.email
           FROM sessions s JOIN users u ON s.user_id = u.id
           WHERE s.token = ? AND s.expires_at > ?""",
        (token, datetime.now(timezone.utc).isoformat()),
    )
    user = await row.fetchone()
    if not user:
        return None
    return {"id": user["id"], "username": user["username"], "email": user["email"],
            "name": user["username"], "initials": user["username"][:2].upper()}


async def destroy_session(db, token: str) -> None:
    await db.execute("DELETE FROM sessions WHERE token = ?", (token,))
    await db.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/auth.py tests/test_auth.py
git commit -m "feat: add auth module with password hashing and session management"
```

---

### Task 4: Auth Module — Session Tests with DB

**Files:**
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests for session and username validation**

Append to `tests/test_auth.py`:

```python
import aiosqlite
from app.auth import create_session, get_current_user, validate_username, hash_password

SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sessions_token ON sessions(token);
"""


@pytest.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.executescript(SCHEMA)
        await conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("testuser", "test@example.com", hash_password("pass123")),
        )
        await conn.commit()
        yield conn


@pytest.mark.asyncio
async def test_create_session_returns_token(db):
    token = await create_session(db, 1)
    assert isinstance(token, str)
    assert len(token) > 20


@pytest.mark.asyncio
async def test_get_current_user_valid_session(db):
    token = await create_session(db, 1)

    class FakeRequest:
        cookies = {"session_token": token}

    user = await get_current_user(FakeRequest(), db)
    assert user is not None
    assert user["username"] == "testuser"
    assert user["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db):
    class FakeRequest:
        cookies = {"session_token": "bogus-token"}

    user = await get_current_user(FakeRequest(), db)
    assert user is None


def test_validate_username_valid():
    assert validate_username("my-user-1") is None


def test_validate_username_uppercase_rejected():
    assert validate_username("MyUser") is not None


def test_validate_username_too_short():
    assert validate_username("a") is not None


def test_validate_username_special_chars():
    assert validate_username("user@name") is not None
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py -v`
Expected: All 10 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth.py
git commit -m "test: add session and username validation tests"
```

---

### Task 5: Login and Register Templates

**Files:**
- Create: `app/templates/login.html`
- Create: `app/templates/register.html`
- Create: `app/templates/choose_username.html`

- [ ] **Step 1: Create login.html**

Create `app/templates/login.html`:

```html
{% extends "base.html" %}
{% block title %}Entrar — resumiu{% endblock %}
{% block content %}
<div class="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-neutral-900 px-4">
  <div class="w-full max-w-sm">
    <!-- Logo -->
    <div class="text-center mb-8">
      <a href="/login">
        <img src="/static/resumiu-logo.svg" alt="resumiu" class="h-10 mx-auto mb-2">
      </a>
      <p class="text-sm text-slate-500 dark:text-neutral-500">Entre na sua conta</p>
    </div>

    <!-- Error -->
    {% if error %}
    <div class="mb-4 text-sm text-red-600 dark:text-red-400 text-center">{{ error }}</div>
    {% endif %}

    <!-- Form -->
    <form method="post" action="/login" class="flex flex-col gap-3.5 mb-6">
      <input type="email" name="email" placeholder="Email" required
        class="w-full px-3.5 py-2.5 bg-transparent border border-slate-300 dark:border-neutral-700 rounded-lg text-slate-800 dark:text-neutral-200 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors">
      <input type="password" name="password" placeholder="Senha" required
        class="w-full px-3.5 py-2.5 bg-transparent border border-slate-300 dark:border-neutral-700 rounded-lg text-slate-800 dark:text-neutral-200 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors">
      <button type="submit"
        class="w-full py-2.5 bg-brand hover:bg-brand-dark text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer">
        Entrar
      </button>
    </form>

    <!-- Divider -->
    <div class="flex items-center gap-3 mb-6">
      <div class="flex-1 h-px bg-slate-300 dark:bg-neutral-700"></div>
      <span class="text-xs text-slate-400 dark:text-neutral-500">ou continue com</span>
      <div class="flex-1 h-px bg-slate-300 dark:bg-neutral-700"></div>
    </div>

    <!-- Social -->
    <div class="flex justify-center gap-4 mb-8">
      <a href="/auth/google" class="w-12 h-12 border border-slate-300 dark:border-neutral-700 rounded-xl flex items-center justify-center hover:bg-slate-50 dark:hover:bg-neutral-800 transition-colors" title="Google">
        <svg class="w-5 h-5" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </a>
      <a href="/auth/github" class="w-12 h-12 border border-slate-300 dark:border-neutral-700 rounded-xl flex items-center justify-center hover:bg-slate-50 dark:hover:bg-neutral-800 transition-colors" title="GitHub">
        <svg class="w-5 h-5 text-slate-800 dark:text-neutral-200" fill="currentColor" viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
      </a>
      <a href="/auth/microsoft" class="w-12 h-12 border border-slate-300 dark:border-neutral-700 rounded-xl flex items-center justify-center hover:bg-slate-50 dark:hover:bg-neutral-800 transition-colors" title="Microsoft">
        <svg class="w-5 h-5" viewBox="0 0 23 23"><rect x="1" y="1" width="10" height="10" fill="#f25022"/><rect x="12" y="1" width="10" height="10" fill="#7fba00"/><rect x="1" y="12" width="10" height="10" fill="#00a4ef"/><rect x="12" y="12" width="10" height="10" fill="#ffb900"/></svg>
      </a>
    </div>

    <!-- Register link -->
    <p class="text-center text-sm text-slate-500 dark:text-neutral-500">
      Não tem conta?
      <a href="/register" class="text-brand hover:underline">Criar conta</a>
    </p>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Create register.html**

Create `app/templates/register.html`:

```html
{% extends "base.html" %}
{% block title %}Criar Conta — resumiu{% endblock %}
{% block content %}
<div class="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-neutral-900 px-4">
  <div class="w-full max-w-sm">
    <!-- Logo -->
    <div class="text-center mb-8">
      <a href="/login">
        <img src="/static/resumiu-logo.svg" alt="resumiu" class="h-10 mx-auto mb-2">
      </a>
      <p class="text-sm text-slate-500 dark:text-neutral-500">Crie sua conta</p>
    </div>

    <!-- Error -->
    {% if error %}
    <div class="mb-4 text-sm text-red-600 dark:text-red-400 text-center">{{ error }}</div>
    {% endif %}

    <!-- Form -->
    <form method="post" action="/register" class="flex flex-col gap-3.5 mb-6">
      <div>
        <input type="text" name="username" placeholder="Username" required pattern="[a-z0-9][a-z0-9-]*" value="{{ username or '' }}"
          class="w-full px-3.5 py-2.5 bg-transparent border border-slate-300 dark:border-neutral-700 rounded-lg text-slate-800 dark:text-neutral-200 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors">
        <p class="mt-1 ml-1 text-xs text-slate-400 dark:text-neutral-500">Apenas letras minúsculas, números e hífens</p>
      </div>
      <input type="email" name="email" placeholder="Email" required value="{{ email or '' }}"
        class="w-full px-3.5 py-2.5 bg-transparent border border-slate-300 dark:border-neutral-700 rounded-lg text-slate-800 dark:text-neutral-200 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors">
      <input type="password" name="password" placeholder="Senha" required
        class="w-full px-3.5 py-2.5 bg-transparent border border-slate-300 dark:border-neutral-700 rounded-lg text-slate-800 dark:text-neutral-200 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors">
      <input type="password" name="password_confirm" placeholder="Confirmar senha" required
        class="w-full px-3.5 py-2.5 bg-transparent border border-slate-300 dark:border-neutral-700 rounded-lg text-slate-800 dark:text-neutral-200 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors">
      <button type="submit"
        class="w-full py-2.5 bg-brand hover:bg-brand-dark text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer">
        Criar conta
      </button>
    </form>

    <!-- Divider -->
    <div class="flex items-center gap-3 mb-6">
      <div class="flex-1 h-px bg-slate-300 dark:bg-neutral-700"></div>
      <span class="text-xs text-slate-400 dark:text-neutral-500">ou continue com</span>
      <div class="flex-1 h-px bg-slate-300 dark:bg-neutral-700"></div>
    </div>

    <!-- Social -->
    <div class="flex justify-center gap-4 mb-8">
      <a href="/auth/google" class="w-12 h-12 border border-slate-300 dark:border-neutral-700 rounded-xl flex items-center justify-center hover:bg-slate-50 dark:hover:bg-neutral-800 transition-colors" title="Google">
        <svg class="w-5 h-5" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
      </a>
      <a href="/auth/github" class="w-12 h-12 border border-slate-300 dark:border-neutral-700 rounded-xl flex items-center justify-center hover:bg-slate-50 dark:hover:bg-neutral-800 transition-colors" title="GitHub">
        <svg class="w-5 h-5 text-slate-800 dark:text-neutral-200" fill="currentColor" viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
      </a>
      <a href="/auth/microsoft" class="w-12 h-12 border border-slate-300 dark:border-neutral-700 rounded-xl flex items-center justify-center hover:bg-slate-50 dark:hover:bg-neutral-800 transition-colors" title="Microsoft">
        <svg class="w-5 h-5" viewBox="0 0 23 23"><rect x="1" y="1" width="10" height="10" fill="#f25022"/><rect x="12" y="1" width="10" height="10" fill="#7fba00"/><rect x="1" y="12" width="10" height="10" fill="#00a4ef"/><rect x="12" y="12" width="10" height="10" fill="#ffb900"/></svg>
      </a>
    </div>

    <!-- Login link -->
    <p class="text-center text-sm text-slate-500 dark:text-neutral-500">
      Já tem conta?
      <a href="/login" class="text-brand hover:underline">Entrar</a>
    </p>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Create choose_username.html**

Create `app/templates/choose_username.html`:

```html
{% extends "base.html" %}
{% block title %}Escolha seu Username — resumiu{% endblock %}
{% block content %}
<div class="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-neutral-900 px-4">
  <div class="w-full max-w-sm">
    <!-- Logo -->
    <div class="text-center mb-8">
      <img src="/static/resumiu-logo.svg" alt="resumiu" class="h-10 mx-auto mb-2">
      <p class="text-sm text-slate-500 dark:text-neutral-500">Escolha seu username</p>
    </div>

    <!-- Error -->
    {% if error %}
    <div class="mb-4 text-sm text-red-600 dark:text-red-400 text-center">{{ error }}</div>
    {% endif %}

    <!-- Form -->
    <form method="post" action="/auth/choose-username" class="flex flex-col gap-3.5">
      <div>
        <input type="text" name="username" placeholder="Username" required pattern="[a-z0-9][a-z0-9-]*" value="{{ username or '' }}"
          class="w-full px-3.5 py-2.5 bg-transparent border border-slate-300 dark:border-neutral-700 rounded-lg text-slate-800 dark:text-neutral-200 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors">
        <p class="mt-1 ml-1 text-xs text-slate-400 dark:text-neutral-500">Apenas letras minúsculas, números e hífens</p>
      </div>
      <button type="submit"
        class="w-full py-2.5 bg-brand hover:bg-brand-dark text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer">
        Continuar
      </button>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/login.html app/templates/register.html app/templates/choose_username.html
git commit -m "feat: add login, register, and choose-username templates"
```

---

### Task 6: Auth Routes — Login, Register, Logout

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Write failing tests for login and register routes**

Append to `tests/test_auth.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

route_client = TestClient(app)


def test_login_page_returns_200():
    response = route_client.get("/login")
    assert response.status_code == 200
    assert "Entre na sua conta" in response.text


def test_register_page_returns_200():
    response = route_client.get("/register")
    assert response.status_code == 200
    assert "Crie sua conta" in response.text


def test_home_redirects_to_login_when_unauthenticated():
    response = route_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py::test_login_page_returns_200 tests/test_auth.py::test_register_page_returns_200 tests/test_auth.py::test_home_redirects_to_login_when_unauthenticated -v`
Expected: FAIL — routes don't exist yet / home doesn't redirect

- [ ] **Step 3: Add auth routes and protect existing routes in main.py**

Modify `app/main.py` — add imports and auth routes. Replace the existing imports and add the new routes. Here is the full updated file:

```python
import markdown as md

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import (
    create_session,
    destroy_session,
    get_current_user,
    hash_password,
    set_session_cookie,
    validate_username,
    verify_password,
    SESSION_COOKIE,
)
from app.database import get_db

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- Mock data (unchanged) ---

MOCK_PROJECTS = [
    {"id": 1, "name": "Projeto Alpha",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-teal-400 to-teal-700"},
    {"id": 2, "name": "Projeto Beta",    "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-teal-300 to-cyan-600"},
    {"id": 3, "name": "Projeto Gamma",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-emerald-400 to-teal-600"},
    {"id": 4, "name": "Projeto Delta",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-cyan-400 to-teal-500"},
    {"id": 5, "name": "Projeto Epsilon", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-teal-500 to-emerald-700"},
    {"id": 6, "name": "Projeto Zeta",    "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-cyan-300 to-teal-600"},
]

_COLLECTION_COLORS = [
    "bg-gradient-to-br from-teal-300 to-teal-600",
    "bg-gradient-to-br from-cyan-400 to-teal-700",
    "bg-gradient-to-br from-emerald-300 to-teal-500",
    "bg-gradient-to-br from-teal-400 to-cyan-600",
    "bg-gradient-to-br from-teal-500 to-emerald-600",
    "bg-gradient-to-br from-cyan-300 to-teal-500",
]

MOCK_COLLECTIONS = {
    project["id"]: [
        {
            "id": project["id"] * 10 + i,
            "name": f"Coleção {i + 1}",
            "thumbnail_url": None,
            "placeholder_color": _COLLECTION_COLORS[i],
        }
        for i in range(6)
    ]
    for project in MOCK_PROJECTS
}


def _build_mock_topics():
    """Generate mock topics for every collection."""
    topics = {}
    detail_id_counter = 1000
    details = {}

    topic_names = ["Introdução", "Conceitos Fundamentais", "Aplicações Práticas"]
    subtopic_templates = [
        ["Visão Geral", "Contexto Histórico"],
        ["Definições", "Princípios", "Modelos"],
        ["Estudo de Caso", "Exercícios"],
    ]
    detail_templates = [
        ["Resumo do tema", "Material complementar", "Vídeo explicativo"],
        ["Glossário de termos", "Diagrama conceitual"],
        ["Exemplo resolvido", "Exercício proposto", "Vídeo da aula"],
    ]

    sample_markdown = (
        "## Resumo\n\n"
        "Este é um conteúdo de exemplo em **markdown**.\n\n"
        "- Ponto importante 1\n"
        "- Ponto importante 2\n"
        "- Ponto importante 3\n\n"
        "### Observações\n\n"
        "Texto adicional com `código inline` e mais detalhes sobre o tópico."
    )

    for project in MOCK_PROJECTS:
        for col in MOCK_COLLECTIONS[project["id"]]:
            col_topics = []
            for t_idx, t_name in enumerate(topic_names):
                subtopics = []
                for s_idx, s_name in enumerate(subtopic_templates[t_idx]):
                    detail_list = []
                    for d_idx, d_name in enumerate(detail_templates[t_idx]):
                        detail_id_counter += 1
                        has_content = (d_idx % 2 == 0)
                        detail_list.append({
                            "id": detail_id_counter,
                            "name": d_name,
                            "has_content": has_content,
                        })
                        if has_content:
                            variant = detail_id_counter % 3
                            if variant == 0:
                                details[detail_id_counter] = {
                                    "name": d_name,
                                    "youtube_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                                    "content_md": sample_markdown,
                                }
                            elif variant == 1:
                                details[detail_id_counter] = {
                                    "name": d_name,
                                    "youtube_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                                    "content_md": None,
                                }
                            else:
                                details[detail_id_counter] = {
                                    "name": d_name,
                                    "youtube_url": None,
                                    "content_md": sample_markdown,
                                }
                    subtopics.append({
                        "id": col["id"] * 100 + t_idx * 10 + s_idx,
                        "name": s_name,
                        "details": detail_list,
                    })
                col_topics.append({
                    "id": col["id"] * 10 + t_idx,
                    "name": t_name,
                    "subtopics": subtopics,
                })
            topics[col["id"]] = col_topics
    return topics, details


MOCK_TOPICS, MOCK_DETAILS = _build_mock_topics()


# --- Auth helper dependency ---

async def require_auth(request: Request, db=Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


# --- Public auth routes ---

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})


@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db),
):
    row = await db.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
    user = await row.fetchone()
    if not user or not user["password_hash"] or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request=request, name="login.html",
            context={"error": "Email ou senha incorretos."},
            status_code=422,
        )
    token = await create_session(db, user["id"])
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, token)
    return response


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={})


@app.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db=Depends(get_db),
):
    # Validate
    username = username.strip().lower()
    err = validate_username(username)
    if err:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": err, "username": username, "email": email},
            status_code=422,
        )
    if password != password_confirm:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": "As senhas não coincidem.", "username": username, "email": email},
            status_code=422,
        )
    # Check uniqueness
    row = await db.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
    if await row.fetchone():
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": "Email ou username já em uso.", "username": username, "email": email},
            status_code=422,
        )
    # Create user
    cursor = await db.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, hash_password(password)),
    )
    await db.commit()
    token = await create_session(db, cursor.lastrowid)
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, token)
    return response


@app.get("/logout")
async def logout(request: Request, db=Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await destroy_session(db, token)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


# --- Protected routes ---

@app.get("/")
async def home(request: Request, user=Depends(require_auth)):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": user, "projects": MOCK_PROJECTS},
    )


def _collect_content_details(topics_list):
    """Collect all details with content from a topics list, enriched for the drawer."""
    items = []
    for topic in topics_list:
        for subtopic in topic["subtopics"]:
            for detail in subtopic["details"]:
                if not detail["has_content"]:
                    continue
                full = MOCK_DETAILS.get(detail["id"])
                if not full:
                    continue
                thumbnail_url = None
                detail_type = "document"
                yt = full.get("youtube_url")
                if yt:
                    detail_type = "video"
                    vid = yt.rsplit("/", 1)[-1]
                    thumbnail_url = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"
                items.append({
                    "id": detail["id"],
                    "name": full["name"],
                    "type": detail_type,
                    "thumbnail_url": thumbnail_url,
                })
    return items


@app.get("/projects/{project_id}")
async def project_topics(request: Request, project_id: int, user=Depends(require_auth)):
    project = next((p for p in MOCK_PROJECTS if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404)
    first_collection = MOCK_COLLECTIONS[project_id][0]
    topics_list = MOCK_TOPICS.get(first_collection["id"], [])
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context={
            "user": user,
            "project": project,
            "topics": topics_list,
            "drawer_items": _collect_content_details(topics_list),
        },
    )


@app.get("/projects/{project_id}/collections/{collection_id}")
async def topics(request: Request, project_id: int, collection_id: int, user=Depends(require_auth)):
    project = next((p for p in MOCK_PROJECTS if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404)
    collection = next(
        (c for c in MOCK_COLLECTIONS[project_id] if c["id"] == collection_id),
        None,
    )
    if not collection:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context={
            "user": user,
            "project": project,
            "collection": collection,
            "topics": MOCK_TOPICS.get(collection_id, []),
        },
    )


@app.get("/htmx/details/{detail_id}")
async def htmx_detail(request: Request, detail_id: int):
    detail = MOCK_DETAILS.get(detail_id)
    if not detail:
        raise HTTPException(status_code=404)
    content_html = None
    if detail.get("content_md"):
        content_html = md.markdown(detail["content_md"])
    return templates.TemplateResponse(
        request=request,
        name="partials/detail_modal.html",
        context={
            "detail": {
                "name": detail["name"],
                "youtube_url": detail.get("youtube_url"),
                "content_html": content_html,
            }
        },
    )


@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html")
```

Note: The `require_auth` dependency raises `HTTPException(status_code=303)` with a Location header. FastAPI's default exception handler will use the 303 status and Location header, effectively redirecting the browser. If this doesn't work cleanly, we'll swap to a custom exception handler in the next step.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py -v`
Expected: All tests pass. Note that `test_home_redirects_to_login_when_unauthenticated` should get a 303.

Note: Existing tests in `test_home.py` will now fail because they hit `/` without auth. We'll fix these in a later step.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_auth.py
git commit -m "feat: add login/register/logout routes and protect existing routes"
```

---

### Task 7: Fix Existing Tests for Auth

**Files:**
- Modify: `tests/test_home.py`
- Modify: `tests/test_collections.py` (if it hits protected routes)
- Modify: `tests/test_topics.py` (if it hits protected routes)

- [ ] **Step 1: Create a test helper for authenticated requests**

Create `tests/conftest.py`:

```python
import pytest
import aiosqlite
from fastapi.testclient import TestClient
from app.main import app
from app.auth import hash_password, create_session

SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE TABLE oauth_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);
"""


@pytest.fixture
def auth_client(tmp_path):
    """TestClient with an authenticated session cookie.

    Patches get_db to use an in-memory SQLite with auth tables + a test user.
    """
    import asyncio
    from app.database import get_db

    db_path = str(tmp_path / "test.db")

    async def setup_db():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.executescript(SCHEMA)
            await db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("testuser", "test@example.com", hash_password("pass123")),
            )
            await db.commit()
            token = await create_session(db, 1)
            return token

    token = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(setup_db())

    async def override_get_db():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, cookies={"session_token": token})
    yield client
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Update test_home.py to use auth_client**

Replace contents of `tests/test_home.py`:

```python
def test_home_returns_200(auth_client):
    response = auth_client.get("/")
    assert response.status_code == 200


def test_home_contains_projetos_title(auth_client):
    response = auth_client.get("/")
    assert "Projetos" in response.text


def test_home_contains_user_name(auth_client):
    response = auth_client.get("/")
    assert "testuser" in response.text


def test_home_contains_project_names(auth_client):
    response = auth_client.get("/")
    assert "Projeto Alpha" in response.text
    assert "Projeto Beta" in response.text
```

- [ ] **Step 3: Update test_topics.py and test_collections.py similarly**

For each test file that hits protected routes, replace `client = TestClient(app)` with the `auth_client` fixture parameter. Use `auth_client.get(...)` instead of `client.get(...)`.

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_home.py tests/test_topics.py tests/test_collections.py
git commit -m "test: update existing tests to work with auth"
```

---

### Task 8: OAuth2 Setup and Routes

**Files:**
- Modify: `app/auth.py` (add OAuth config)
- Modify: `app/main.py` (add OAuth routes)

- [ ] **Step 1: Add OAuth client configuration to auth.py**

Append to `app/auth.py`:

```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

_google_id = os.getenv("GOOGLE_CLIENT_ID")
_github_id = os.getenv("GITHUB_CLIENT_ID")
_microsoft_id = os.getenv("MICROSOFT_CLIENT_ID")

if _google_id:
    oauth.register(
        name="google",
        client_id=_google_id,
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

if _github_id:
    oauth.register(
        name="github",
        client_id=_github_id,
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )

if _microsoft_id:
    oauth.register(
        name="microsoft",
        client_id=_microsoft_id,
        client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


PROVIDERS = {}
if _google_id:
    PROVIDERS["google"] = oauth.google
if _github_id:
    PROVIDERS["github"] = oauth.github
if _microsoft_id:
    PROVIDERS["microsoft"] = oauth.microsoft
```

- [ ] **Step 2: Add starlette SessionMiddleware for OAuth state**

Add to `app/main.py` after `app = FastAPI()`:

```python
import os
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
)
```

Also add these imports to `app/main.py`:

```python
from app.auth import oauth, PROVIDERS
```

- [ ] **Step 3: Add OAuth routes to main.py**

Add these routes to `app/main.py`:

```python
@app.get("/auth/{provider}")
async def oauth_login(request: Request, provider: str):
    client = PROVIDERS.get(provider)
    if not client:
        raise HTTPException(status_code=404, detail="Provider não configurado")
    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await client.authorize_redirect(request, str(redirect_uri))


@app.get("/auth/{provider}/callback")
async def oauth_callback(request: Request, provider: str, db=Depends(get_db)):
    client = PROVIDERS.get(provider)
    if not client:
        raise HTTPException(status_code=404, detail="Provider não configurado")

    token_data = await client.authorize_access_token(request)

    # Get user info depending on provider
    if provider == "github":
        resp = await client.get("user", token=token_data)
        profile = resp.json()
        provider_user_id = str(profile["id"])
        email = profile.get("email")
        if not email:
            # GitHub may not include email; fetch from emails API
            email_resp = await client.get("user/emails", token=token_data)
            emails = email_resp.json()
            primary = next((e for e in emails if e["primary"]), None)
            email = primary["email"] if primary else None
    else:
        # Google and Microsoft return OIDC userinfo
        userinfo = token_data.get("userinfo", {})
        provider_user_id = userinfo.get("sub", "")
        email = userinfo.get("email")

    if not email:
        return templates.TemplateResponse(
            request=request, name="login.html",
            context={"error": "Não foi possível obter o email do provedor."},
            status_code=422,
        )

    # Check if this OAuth account already linked
    row = await db.execute(
        "SELECT user_id FROM oauth_accounts WHERE provider = ? AND provider_user_id = ?",
        (provider, provider_user_id),
    )
    existing_oauth = await row.fetchone()

    if existing_oauth:
        # Existing OAuth link — just log in
        token = await create_session(db, existing_oauth["user_id"])
        response = RedirectResponse("/", status_code=303)
        set_session_cookie(response, token)
        return response

    # Check if email matches an existing user
    row = await db.execute("SELECT id FROM users WHERE email = ?", (email,))
    existing_user = await row.fetchone()

    if existing_user:
        # Link OAuth to existing user and log in
        await db.execute(
            "INSERT INTO oauth_accounts (user_id, provider, provider_user_id) VALUES (?, ?, ?)",
            (existing_user["id"], provider, provider_user_id),
        )
        await db.commit()
        token = await create_session(db, existing_user["id"])
        response = RedirectResponse("/", status_code=303)
        set_session_cookie(response, token)
        return response

    # New user — need to choose username
    request.session["oauth_email"] = email
    request.session["oauth_provider"] = provider
    request.session["oauth_provider_user_id"] = provider_user_id
    return RedirectResponse("/auth/choose-username", status_code=303)


@app.get("/auth/choose-username")
async def choose_username_page(request: Request):
    if "oauth_email" not in request.session:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request=request, name="choose_username.html", context={})


@app.post("/auth/choose-username")
async def choose_username_submit(
    request: Request,
    username: str = Form(...),
    db=Depends(get_db),
):
    if "oauth_email" not in request.session:
        return RedirectResponse("/login", status_code=303)

    username = username.strip().lower()
    err = validate_username(username)
    if err:
        return templates.TemplateResponse(
            request=request, name="choose_username.html",
            context={"error": err, "username": username},
            status_code=422,
        )

    # Check username uniqueness
    row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if await row.fetchone():
        return templates.TemplateResponse(
            request=request, name="choose_username.html",
            context={"error": "Username já em uso.", "username": username},
            status_code=422,
        )

    # Create user + OAuth link
    email = request.session["oauth_email"]
    provider = request.session["oauth_provider"]
    provider_user_id = request.session["oauth_provider_user_id"]

    cursor = await db.execute(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        (username, email),
    )
    user_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO oauth_accounts (user_id, provider, provider_user_id) VALUES (?, ?, ?)",
        (user_id, provider, provider_user_id),
    )
    await db.commit()

    # Clear OAuth session data
    request.session.pop("oauth_email", None)
    request.session.pop("oauth_provider", None)
    request.session.pop("oauth_provider_user_id", None)

    token = await create_session(db, user_id)
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, token)
    return response
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add app/auth.py app/main.py
git commit -m "feat: add OAuth2 login routes (Google, GitHub, Microsoft)"
```

---

### Task 9: Fix Redirect Mechanism for Protected Routes

**Files:**
- Modify: `app/main.py`

The `HTTPException(status_code=303)` approach for redirects may not work cleanly with FastAPI's default exception handler. Replace it with a proper pattern.

- [ ] **Step 1: Replace require_auth with a proper redirect dependency**

In `app/main.py`, replace the `require_auth` function:

```python
from starlette.exceptions import HTTPException as StarletteHTTPException

class AuthRedirect(Exception):
    pass

@app.exception_handler(AuthRedirect)
async def auth_redirect_handler(request: Request, exc: AuthRedirect):
    return RedirectResponse("/login", status_code=303)


async def require_auth(request: Request, db=Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise AuthRedirect()
    return user
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass, including `test_home_redirects_to_login_when_unauthenticated`

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "fix: use custom exception for auth redirect"
```

---

### Task 10: Manual Smoke Test

- [ ] **Step 1: Add SECRET_KEY to .env**

Add to `.env`:

```
SECRET_KEY=local-dev-secret-key-change-in-prod
```

- [ ] **Step 2: Run migrations and start dev server**

```bash
make migrate
make dev
```

- [ ] **Step 3: Verify login flow**

1. Open `http://localhost:8000` → should redirect to `/login`
2. Click "Criar conta" → navigate to `/register`
3. Fill in username: `testuser`, email: `test@test.com`, password: `test123`, confirm: `test123` → submit
4. Should redirect to `/` with the home page showing projects
5. Click user menu → "Sair" → should redirect to `/login`
6. Log in with `test@test.com` / `test123` → should redirect to `/`
7. Verify social icons link to `/auth/google`, `/auth/github`, `/auth/microsoft` (will 404 without credentials configured, which is expected)

- [ ] **Step 4: Commit any final adjustments**

```bash
git add -A
git commit -m "chore: finalize login system"
```
