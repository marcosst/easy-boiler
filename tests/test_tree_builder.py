import asyncio
import json
import aiosqlite
import pytest
from app.services.tree_builder import build_tree_for_subject, rebuild_content_json

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
            await db.execute(
                "INSERT INTO library_items (subject_id, name, type, url, position) VALUES (1, 'V', 'youtube', 'http://x', 0)"
            )
            await db.execute(
                "INSERT INTO knowledge_items (library_id, topico, subtopico, acao, timestamp, url) VALUES (1, 'Cadastro', 'Upload', 'Selecionar arquivo', '00:01:03', 'https://www.youtube.com/watch?v=abc&t=63s')"
            )
            await db.execute(
                "INSERT INTO knowledge_items (library_id, topico, subtopico, acao, timestamp, url) VALUES (1, 'Cadastro', 'Upload', 'Confirmar envio', '00:02:00', 'https://www.youtube.com/watch?v=abc&t=120s')"
            )
            await db.execute(
                "INSERT INTO knowledge_items (library_id, topico, subtopico, acao, timestamp, url) VALUES (1, 'Config', 'Ajustes', 'Definir nome', '00:03:00', 'https://www.youtube.com/watch?v=abc&t=180s')"
            )
            await db.commit()
    asyncio.run(_setup())
    return db_path


def test_build_tree(setup_db):
    async def _test():
        async with aiosqlite.connect(setup_db) as db:
            db.row_factory = aiosqlite.Row
            tree = await build_tree_for_subject(db, subject_id=1)
            assert "topicos" in tree
            assert len(tree["topicos"]) == 2
            cadastro = next(t for t in tree["topicos"] if t["titulo"] == "Cadastro")
            assert len(cadastro["subtopicos"]) == 1
            upload = cadastro["subtopicos"][0]
            assert upload["titulo"] == "Upload"
            assert len(upload["passos"]) == 2
            assert upload["passos"][0]["acao"] == "Selecionar arquivo"
            assert upload["passos"][0]["library_id"] == 1
            assert upload["passos"][0]["timestamp"] == "00:01:03"
            assert upload["passos"][0]["url"] == "https://www.youtube.com/watch?v=abc&t=63s"
            assert upload["passos"][0]["pagina"] is None
            assert upload["passos"][0]["file_path"] is None
    asyncio.run(_test())


def test_rebuild_content_json(setup_db):
    async def _test():
        async with aiosqlite.connect(setup_db) as db:
            db.row_factory = aiosqlite.Row
            await rebuild_content_json(db, subject_id=1)
            cursor = await db.execute("SELECT content_json FROM subjects WHERE id = 1")
            row = await cursor.fetchone()
            data = json.loads(row["content_json"])
            assert len(data["topicos"]) == 2
    asyncio.run(_test())


def test_empty_tree(setup_db):
    async def _test():
        async with aiosqlite.connect(setup_db) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("DELETE FROM knowledge_items")
            await db.commit()
            tree = await build_tree_for_subject(db, subject_id=1)
            assert tree == {"topicos": []}
    asyncio.run(_test())
