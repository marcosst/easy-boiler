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


def test_oauth_unconfigured_provider_returns_404():
    response = route_client.get("/auth/unconfigured-provider", follow_redirects=False)
    assert response.status_code == 404
