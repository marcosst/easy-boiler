import asyncio
import aiosqlite
import pytest
from app.services.taxonomy_service import get_taxonomy_for_subject

SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    shortname TEXT NOT NULL UNIQUE,
    is_public INTEGER NOT NULL DEFAULT 0,
    image_path TEXT,
    content_json TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE library_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    url TEXT,
    file_path TEXT,
    image_path TEXT,
    subtitle_path TEXT,
    metadata TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME DEFAULT NULL,
    processed_at DATETIME DEFAULT NULL
);
CREATE TABLE knowledge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL REFERENCES library_items(id) ON DELETE CASCADE,
    topico TEXT NOT NULL,
    subtopico TEXT NOT NULL,
    acao TEXT NOT NULL,
    timestamp TEXT,
    pagina INTEGER,
    trecho_referencia TEXT NOT NULL DEFAULT '',
    file_path TEXT,
    url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def setup_db(db_path):
    async def _setup():
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.executescript(SCHEMA)
            await db.execute("INSERT INTO users (username, email) VALUES ('u', 'u@e.com')")
            await db.execute("INSERT INTO subjects (name, shortname, owner_id) VALUES ('S', 'ss', 1)")
            await db.commit()
    asyncio.run(_setup())
    return db_path


def test_empty_taxonomy(setup_db):
    async def _test():
        async with aiosqlite.connect(setup_db) as db:
            db.row_factory = aiosqlite.Row
            result = await get_taxonomy_for_subject(db, subject_id=1)
            assert result == {"topicos": []}
    asyncio.run(_test())


def test_taxonomy_with_items(setup_db):
    async def _test():
        async with aiosqlite.connect(setup_db) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "INSERT INTO library_items (subject_id, name, type, url, position) VALUES (1, 'V', 'youtube', 'http://x', 0)"
            )
            await db.execute(
                "INSERT INTO knowledge_items (library_id, topico, subtopico, acao, timestamp, url) VALUES (1, 'Cadastro', 'Upload', 'Acao1', '00:00:01', 'http://x')"
            )
            await db.execute(
                "INSERT INTO knowledge_items (library_id, topico, subtopico, acao, timestamp, url) VALUES (1, 'Cadastro', 'Config', 'Acao2', '00:00:02', 'http://x')"
            )
            await db.execute(
                "INSERT INTO knowledge_items (library_id, topico, subtopico, acao, timestamp, url) VALUES (1, 'Outro', 'Sub1', 'Acao3', '00:00:03', 'http://x')"
            )
            await db.commit()
            result = await get_taxonomy_for_subject(db, subject_id=1)
            assert len(result["topicos"]) == 2
            cadastro = next(t for t in result["topicos"] if t["titulo"] == "Cadastro")
            assert set(cadastro["subtopicos"]) == {"Upload", "Config"}
    asyncio.run(_test())
