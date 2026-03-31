import asyncio
import json
import pytest
import aiosqlite
from fastapi.testclient import TestClient
from app.main import app
from app.auth import hash_password, create_session
from app.database import get_db

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
CREATE TABLE subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    shortname TEXT NOT NULL UNIQUE
                     CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    image_path TEXT,
    content_json TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE library_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('youtube', 'pdf')),
    url TEXT,
    file_path TEXT,
    image_path TEXT,
    subtitle_path TEXT,
    metadata TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME DEFAULT NULL
);
CREATE INDEX idx_library_items_subject ON library_items(subject_id);
CREATE TABLE knowledge_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id        INTEGER NOT NULL REFERENCES library_items(id) ON DELETE CASCADE,
    topico            TEXT NOT NULL,
    subtopico         TEXT NOT NULL,
    acao              TEXT NOT NULL,
    timestamp         TEXT,
    pagina            INTEGER,
    trecho_referencia TEXT NOT NULL DEFAULT '',
    file_path         TEXT,
    url               TEXT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_knowledge_items_library ON knowledge_items(library_id);
"""

TEST_CONTENT_JSON = json.dumps({
    "topicos": [{
        "titulo": "Introducao",
        "subtopicos": [{
            "titulo": "Visao Geral",
            "passos": [{"acao": "Exemplo", "timestamp": None, "pagina": None, "trecho_referencia": "", "file_path": None, "url": None}]
        }]
    }]
})


@pytest.fixture
def auth_client(tmp_path):
    db_path = str(tmp_path / "test.db")

    async def setup_db():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.executescript(SCHEMA)
            await db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("testuser", "test@example.com", hash_password("pass123")),
            )
            await db.execute(
                "INSERT INTO subjects (name, shortname, owner_id, content_json) VALUES (?, ?, ?, ?)",
                ("Assunto Teste", "assunto-teste", 1, TEST_CONTENT_JSON),
            )
            await db.execute(
                "INSERT INTO subjects (name, shortname, owner_id, content_json) VALUES (?, ?, ?, ?)",
                ("Segundo Assunto", "segundo-assunto", 1, TEST_CONTENT_JSON),
            )
            await db.commit()
            token = await create_session(db, 1)
            return token

    loop = asyncio.new_event_loop()
    token = loop.run_until_complete(setup_db())
    loop.close()

    async def override_get_db():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, cookies={"session_token": token})
    yield client
    app.dependency_overrides.clear()
