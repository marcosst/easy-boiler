# LLM Topic Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After saving a YouTube video to the library, automatically classify its subtitles into topics/subtopics/actions via OpenAI GPT-5.4, persist as `knowledge_items`, and update the accordion in real-time.

**Architecture:** Two chained HTMX requests — Request 1 (existing save) downloads subtitles + saves the library item, Request 2 (new classify endpoint) calls the LLM + persists knowledge items + rebuilds the content_json tree. The modal closes after Request 1, a spinner shows over the accordion during Request 2.

**Tech Stack:** FastAPI, OpenAI Python SDK, Pydantic v2, aiosqlite, HTMX, Jinja2

---

### Task 1: Database Migration — `knowledge_items` table + `processed_at` column

**Files:**
- Create: `db/migrations/20260330200001_knowledge_items.sql`
- Modify: `tests/conftest.py:10-62` (add new tables to test schema)

- [ ] **Step 1: Create the migration file**

```sql
-- migrate:up
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

ALTER TABLE library_items ADD COLUMN processed_at DATETIME DEFAULT NULL;

-- migrate:down
DROP TABLE IF EXISTS knowledge_items;

-- SQLite doesn't support DROP COLUMN before 3.35.0, so we recreate:
CREATE TABLE library_items_backup AS SELECT id, subject_id, name, type, url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at, deleted_at FROM library_items;
DROP TABLE library_items;
CREATE TABLE library_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id    INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    type          TEXT    NOT NULL CHECK(type IN ('youtube', 'pdf')),
    url           TEXT,
    file_path     TEXT,
    image_path    TEXT,
    subtitle_path TEXT,
    metadata      TEXT,
    position      INTEGER NOT NULL DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at    DATETIME DEFAULT NULL
);
INSERT INTO library_items SELECT * FROM library_items_backup;
DROP TABLE library_items_backup;
CREATE INDEX idx_library_items_subject ON library_items(subject_id);
```

- [ ] **Step 2: Update test schema in conftest.py**

Add to the `SCHEMA` string in `tests/conftest.py`, after the `library_items` table and its index:

```python
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
```

Also add `processed_at DATETIME DEFAULT NULL` to the `library_items` CREATE TABLE in the test schema (after the `updated_at` column, before the closing paren).

- [ ] **Step 3: Run the migration**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make migrate`
Expected: Migration applies successfully.

- [ ] **Step 4: Verify the migration**

Run: `cd /home/ubuntu/aaaa/easy-boiler && sqlite3 data/app.db ".schema knowledge_items" && sqlite3 data/app.db "PRAGMA table_info(library_items)" | grep processed_at`
Expected: Table schema matches, `processed_at` column exists.

- [ ] **Step 5: Commit**

```bash
git add db/migrations/20260330200001_knowledge_items.sql tests/conftest.py db/schema.sql
git commit -m "feat: add knowledge_items table and processed_at column"
```

---

### Task 2: Pydantic Schema — LLM Output Validation

**Files:**
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/llm_output.py`
- Create: `tests/test_llm_output_schema.py`

- [ ] **Step 1: Create the schemas package**

Create empty `app/schemas/__init__.py`:

```python
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_llm_output_schema.py`:

```python
import pytest
from pydantic import ValidationError
from app.schemas.llm_output import ItemLLM, ResultadoLLM


def test_valid_item():
    item = ItemLLM(topico="Cadastro", subtopico="Upload", acao="Selecionar arquivo", timestamp="00:01:03")
    assert item.topico == "Cadastro"
    assert item.timestamp == "00:01:03"


def test_timestamp_format_invalid():
    with pytest.raises(ValidationError):
        ItemLLM(topico="X", subtopico="Y", acao="Z", timestamp="1:2:3")


def test_timestamp_format_invalid_letters():
    with pytest.raises(ValidationError):
        ItemLLM(topico="X", subtopico="Y", acao="Z", timestamp="ab:cd:ef")


def test_empty_topico_rejected():
    with pytest.raises(ValidationError):
        ItemLLM(topico="", subtopico="Y", acao="Z", timestamp="00:00:00")


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        ItemLLM(topico="X", subtopico="Y", acao="Z", timestamp="00:00:00", url="http://x.com")


def test_resultado_valid():
    data = {
        "itens": [
            {"topico": "A", "subtopico": "B", "acao": "C", "timestamp": "00:00:01"},
            {"topico": "A", "subtopico": "B", "acao": "D", "timestamp": "00:01:00"},
        ]
    }
    result = ResultadoLLM(**data)
    assert len(result.itens) == 2


def test_resultado_extra_fields_rejected():
    with pytest.raises(ValidationError):
        ResultadoLLM(itens=[], extra_field="bad")


def test_whitespace_stripped():
    item = ItemLLM(topico="  Cadastro  ", subtopico=" Upload ", acao=" Acao ", timestamp="00:00:01")
    assert item.topico == "Cadastro"
    assert item.subtopico == "Upload"
    assert item.acao == "Acao"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_llm_output_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas'`

- [ ] **Step 4: Write the implementation**

Create `app/schemas/llm_output.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topico: str = Field(min_length=1)
    subtopico: str = Field(min_length=1)
    acao: str = Field(min_length=1)
    timestamp: str = Field(pattern=r"^\d{2}:\d{2}:\d{2}$")

    @field_validator("topico", "subtopico", "acao", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class ResultadoLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itens: list[ItemLLM]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_llm_output_schema.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/__init__.py app/schemas/llm_output.py tests/test_llm_output_schema.py
git commit -m "feat: add Pydantic schema for LLM output validation"
```

---

### Task 3: URL Builder Service

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/url_builder.py`
- Create: `tests/test_url_builder.py`

- [ ] **Step 1: Create the services package**

Create empty `app/services/__init__.py`:

```python
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_url_builder.py`:

```python
from app.services.url_builder import timestamp_to_seconds, build_step_url


def test_timestamp_to_seconds_basic():
    assert timestamp_to_seconds("00:01:03") == 63


def test_timestamp_to_seconds_zero():
    assert timestamp_to_seconds("00:00:00") == 0


def test_timestamp_to_seconds_hours():
    assert timestamp_to_seconds("01:30:00") == 5400


def test_timestamp_to_seconds_all_parts():
    assert timestamp_to_seconds("02:15:45") == 8145


def test_build_step_url():
    url = build_step_url("abc123", "00:01:03")
    assert url == "https://www.youtube.com/watch?v=abc123&t=63s"


def test_build_step_url_zero():
    url = build_step_url("xyz789", "00:00:00")
    assert url == "https://www.youtube.com/watch?v=xyz789&t=0s"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_url_builder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services'`

- [ ] **Step 4: Write the implementation**

Create `app/services/url_builder.py`:

```python
def timestamp_to_seconds(timestamp: str) -> int:
    """Convert HH:MM:SS to total seconds."""
    parts = timestamp.split(":")
    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
    return h * 3600 + m * 60 + s


def build_step_url(youtube_id: str, timestamp: str) -> str:
    """Build YouTube URL with timestamp parameter."""
    seconds = timestamp_to_seconds(timestamp)
    return f"https://www.youtube.com/watch?v={youtube_id}&t={seconds}s"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_url_builder.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/__init__.py app/services/url_builder.py tests/test_url_builder.py
git commit -m "feat: add URL builder service for YouTube timestamp links"
```

---

### Task 4: Taxonomy Service

**Files:**
- Create: `app/services/taxonomy_service.py`
- Create: `tests/test_taxonomy_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_taxonomy_service.py`:

```python
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
    asyncio.get_event_loop().run_until_complete(_setup())
    return db_path


def test_empty_taxonomy(setup_db):
    async def _test():
        async with aiosqlite.connect(setup_db) as db:
            db.row_factory = aiosqlite.Row
            result = await get_taxonomy_for_subject(db, subject_id=1)
            assert result == {"topicos": []}
    asyncio.get_event_loop().run_until_complete(_test())


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
    asyncio.get_event_loop().run_until_complete(_test())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_taxonomy_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.taxonomy_service'`

- [ ] **Step 3: Write the implementation**

Create `app/services/taxonomy_service.py`:

```python
import aiosqlite


async def get_taxonomy_for_subject(db: aiosqlite.Connection, subject_id: int) -> dict:
    """Extract minimal taxonomy (topics + subtopic names) for a subject.

    Returns {"topicos": [{"titulo": "...", "subtopicos": ["...", ...]}]}
    """
    cursor = await db.execute(
        """
        SELECT DISTINCT ki.topico, ki.subtopico
        FROM knowledge_items ki
        JOIN library_items li ON ki.library_id = li.id
        WHERE li.subject_id = ? AND li.deleted_at IS NULL
        ORDER BY ki.topico, ki.subtopico
        """,
        (subject_id,),
    )
    rows = await cursor.fetchall()

    topics: dict[str, list[str]] = {}
    for row in rows:
        topico = row["topico"]
        subtopico = row["subtopico"]
        if topico not in topics:
            topics[topico] = []
        if subtopico not in topics[topico]:
            topics[topico].append(subtopico)

    return {
        "topicos": [
            {"titulo": titulo, "subtopicos": subs}
            for titulo, subs in topics.items()
        ]
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_taxonomy_service.py -v`
Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/taxonomy_service.py tests/test_taxonomy_service.py
git commit -m "feat: add taxonomy service to extract existing topic structure"
```

---

### Task 5: Tree Builder Service

**Files:**
- Create: `app/services/tree_builder.py`
- Create: `tests/test_tree_builder.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tree_builder.py`:

```python
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
    asyncio.get_event_loop().run_until_complete(_setup())
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
    asyncio.get_event_loop().run_until_complete(_test())


def test_rebuild_content_json(setup_db):
    async def _test():
        async with aiosqlite.connect(setup_db) as db:
            db.row_factory = aiosqlite.Row
            await rebuild_content_json(db, subject_id=1)
            cursor = await db.execute("SELECT content_json FROM subjects WHERE id = 1")
            row = await cursor.fetchone()
            data = json.loads(row["content_json"])
            assert len(data["topicos"]) == 2
    asyncio.get_event_loop().run_until_complete(_test())


def test_empty_tree(setup_db):
    async def _test():
        async with aiosqlite.connect(setup_db) as db:
            db.row_factory = aiosqlite.Row
            # Delete all knowledge items
            await db.execute("DELETE FROM knowledge_items")
            await db.commit()
            tree = await build_tree_for_subject(db, subject_id=1)
            assert tree == {"topicos": []}
    asyncio.get_event_loop().run_until_complete(_test())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_tree_builder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.tree_builder'`

- [ ] **Step 3: Write the implementation**

Create `app/services/tree_builder.py`:

```python
import json
import aiosqlite


async def build_tree_for_subject(db: aiosqlite.Connection, subject_id: int) -> dict:
    """Build the reading tree from knowledge_items for a subject.

    Returns {"topicos": [{"titulo": ..., "subtopicos": [{"titulo": ..., "passos": [...]}]}]}
    """
    cursor = await db.execute(
        """
        SELECT ki.library_id, ki.topico, ki.subtopico, ki.acao,
               ki.timestamp, ki.pagina, ki.trecho_referencia, ki.file_path, ki.url
        FROM knowledge_items ki
        JOIN library_items li ON ki.library_id = li.id
        WHERE li.subject_id = ? AND li.deleted_at IS NULL
        ORDER BY ki.topico, ki.subtopico, ki.library_id, ki.timestamp
        """,
        (subject_id,),
    )
    rows = await cursor.fetchall()

    topics_order: list[str] = []
    topics: dict[str, dict[str, list[dict]]] = {}

    for row in rows:
        topico = row["topico"]
        subtopico = row["subtopico"]

        if topico not in topics:
            topics[topico] = {}
            topics_order.append(topico)

        if subtopico not in topics[topico]:
            topics[topico][subtopico] = []

        topics[topico][subtopico].append({
            "library_id": row["library_id"],
            "acao": row["acao"],
            "timestamp": row["timestamp"],
            "pagina": row["pagina"],
            "trecho_referencia": row["trecho_referencia"] or "",
            "file_path": row["file_path"],
            "url": row["url"],
        })

    return {
        "topicos": [
            {
                "titulo": topico,
                "subtopicos": [
                    {"titulo": sub, "passos": passos}
                    for sub, passos in topics[topico].items()
                ],
            }
            for topico in topics_order
        ]
    }


async def rebuild_content_json(db: aiosqlite.Connection, subject_id: int) -> dict:
    """Rebuild and save content_json for a subject. Returns the tree."""
    tree = await build_tree_for_subject(db, subject_id)
    await db.execute(
        "UPDATE subjects SET content_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(tree, ensure_ascii=False), subject_id),
    )
    await db.commit()
    return tree
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_tree_builder.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/tree_builder.py tests/test_tree_builder.py
git commit -m "feat: add tree builder service for reading tree generation"
```

---

### Task 6: LLM Classifier Service

**Files:**
- Create: `app/services/llm_classifier.py`
- Create: `tests/test_llm_classifier.py`

- [ ] **Step 1: Add openai dependency**

Run: `cd /home/ubuntu/aaaa/easy-boiler && uv add openai`
Expected: `openai` added to `pyproject.toml` and installed.

- [ ] **Step 2: Write the failing test**

Create `tests/test_llm_classifier.py`:

```python
import json
from unittest.mock import patch, MagicMock
import pytest
from app.services.llm_classifier import classify_transcript, _build_messages
from app.schemas.llm_output import ResultadoLLM


def test_build_messages_empty_taxonomy():
    taxonomy = {"topicos": []}
    transcript = "[00:00:07] selecionar o arquivo\n[00:00:18] salvar o projeto"
    messages = _build_messages(taxonomy, transcript)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Nenhuma taxonomia existente" in messages[1]["content"]
    assert "[00:00:07]" in messages[1]["content"]


def test_build_messages_with_taxonomy():
    taxonomy = {
        "topicos": [
            {"titulo": "Cadastro", "subtopicos": ["Upload", "Config"]}
        ]
    }
    transcript = "[00:00:07] selecionar o arquivo"
    messages = _build_messages(taxonomy, transcript)
    assert "Cadastro" in messages[1]["content"]
    assert "Upload" in messages[1]["content"]


def test_classify_transcript_success():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "itens": [
            {"topico": "Cadastro", "subtopico": "Upload", "acao": "Selecionar arquivo", "timestamp": "00:00:07"}
        ]
    })

    with patch("app.services.llm_classifier._call_openai", return_value=mock_response):
        result = classify_transcript(
            taxonomy={"topicos": []},
            transcript="[00:00:07] selecionar o arquivo",
        )
    assert isinstance(result, ResultadoLLM)
    assert len(result.itens) == 1
    assert result.itens[0].topico == "Cadastro"


def test_classify_transcript_invalid_json():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not valid json"

    with patch("app.services.llm_classifier._call_openai", return_value=mock_response):
        result = classify_transcript(
            taxonomy={"topicos": []},
            transcript="[00:00:07] selecionar o arquivo",
        )
    assert result is None


def test_classify_transcript_pydantic_validation_error():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "itens": [
            {"topico": "", "subtopico": "X", "acao": "Y", "timestamp": "00:00:01"}
        ]
    })

    with patch("app.services.llm_classifier._call_openai", return_value=mock_response):
        result = classify_transcript(
            taxonomy={"topicos": []},
            transcript="[00:00:07] selecionar o arquivo",
        )
    assert result is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_llm_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.llm_classifier'`

- [ ] **Step 4: Write the implementation**

Create `app/services/llm_classifier.py`:

```python
import json
import logging
import os

from openai import OpenAI
from pydantic import ValidationError

from app.schemas.llm_output import ResultadoLLM

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um organizador de transcripts técnicos de vídeo.

Sua tarefa é classificar o conteúdo de um novo transcript usando uma taxonomia já existente de tópicos e subtópicos.

Objetivo:
Reaproveitar ao máximo os tópicos e subtópicos existentes e criar novos apenas quando realmente necessário.

Regras:
- Use a taxonomia existente como referência principal.
- Antes de criar um novo tópico, tente encaixar o conteúdo em um tópico já existente.
- Antes de criar um novo subtópico, tente encaixar o conteúdo em um subtópico já existente dentro do tópico escolhido.
- Reutilize nomes existentes sempre que houver equivalência semântica.
- Não crie novos nomes apenas por variação de vocabulário.
- Normalize sinônimos para os rótulos já existentes.
- Só crie novo tópico ou subtópico quando houver diferença real de função, etapa ou conceito.
- Evite duplicação semântica.
- Cada item deve representar uma ação concreta e útil para consulta futura.
- Ignore falas de enchimento, repetições e comentários sem valor operacional.
- Se houver dúvida entre reutilizar ou criar novo, prefira reutilizar.
- Não invente conteúdo que não esteja no transcript.

Considere equivalentes, quando fizer sentido:
- enviar / subir / fazer upload
- componente / módulo / item
- atualizar / recarregar / sincronizar
- aplicar / inserir / usar
- configurar / definir / ajustar
- selecionar / escolher

Retorne apenas JSON válido no formato:

{
  "itens": [
    {
      "topico": "",
      "subtopico": "",
      "acao": "",
      "timestamp": "00:00:00"
    }
  ]
}"""


def _build_messages(taxonomy: dict, transcript: str) -> list[dict]:
    """Build the messages list for the OpenAI API call."""
    if taxonomy.get("topicos"):
        taxonomy_text = json.dumps(taxonomy, ensure_ascii=False, indent=2)
    else:
        taxonomy_text = "Nenhuma taxonomia existente ainda."

    user_content = f"Taxonomia existente:\n{taxonomy_text}\n\nTranscript:\n{transcript}"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _call_openai(messages: list[dict]):
    """Make the actual OpenAI API call. Separated for easy mocking."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client.chat.completions.create(
        model="gpt-5.4",
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"},
    )


def classify_transcript(taxonomy: dict, transcript: str) -> ResultadoLLM | None:
    """Classify a transcript using the LLM. Returns validated result or None on failure."""
    messages = _build_messages(taxonomy, transcript)

    try:
        response = _call_openai(messages)
    except Exception:
        logger.exception("OpenAI API call failed")
        return None

    raw_content = response.choices[0].message.content

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON: %s", raw_content[:200])
        return None

    try:
        return ResultadoLLM(**data)
    except ValidationError as exc:
        logger.error("LLM output failed validation: %s", exc)
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_llm_classifier.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock app/services/llm_classifier.py tests/test_llm_classifier.py
git commit -m "feat: add LLM classifier service with OpenAI integration"
```

---

### Task 7: Classify Endpoint + Save Endpoint Modification

**Files:**
- Modify: `app/main.py:838-935` (save endpoint + new classify endpoint)
- Create: `tests/test_classify.py`

- [ ] **Step 1: Write the failing test for the classify endpoint**

Create `tests/test_classify.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_classify_creates_knowledge_items(auth_client, tmp_path):
    """POST /htmx/library/{id}/classify processes subtitles and creates knowledge items."""
    # First create a library item with subtitle_path
    subs_dir = Path("midias/testuser/subtitles")
    subs_dir.mkdir(parents=True, exist_ok=True)
    subs_file = subs_dir / "dQw4w9WgXcQ.txt"
    subs_file.write_text("[00:00:07] selecionar o arquivo\n[00:00:18] salvar o projeto\n", encoding="utf-8")

    # Save item directly (skip Apify by posting a non-youtube type then updating)
    response = auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "youtube",
            "name": "Test Video",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "image_path": "",
        },
    )
    assert response.status_code == 200

    # Mock the LLM classifier
    mock_result_data = {
        "itens": [
            {"topico": "Cadastro", "subtopico": "Upload", "acao": "Selecionar arquivo", "timestamp": "00:00:07"},
            {"topico": "Cadastro", "subtopico": "Upload", "acao": "Salvar projeto", "timestamp": "00:00:18"},
        ]
    }
    from app.schemas.llm_output import ResultadoLLM
    mock_result = ResultadoLLM(**mock_result_data)

    with patch("app.main.classify_transcript", return_value=mock_result):
        response = auth_client.post("/htmx/library/1/classify")

    assert response.status_code == 200

    # Clean up
    subs_file.unlink(missing_ok=True)


def test_classify_no_subtitle_path(auth_client):
    """POST /htmx/library/{id}/classify with no subtitle_path returns 200 (no-op)."""
    # Save a PDF item (no subtitle_path)
    auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "pdf",
            "name": "Test PDF",
            "file_path": "testuser/pdfs/fake.pdf",
            "image_path": "",
        },
    )

    response = auth_client.post("/htmx/library/1/classify")
    assert response.status_code == 200


def test_classify_nonexistent_item(auth_client):
    """POST /htmx/library/999/classify returns 404."""
    response = auth_client.post("/htmx/library/999/classify")
    assert response.status_code == 404


def test_classify_llm_failure_graceful(auth_client, tmp_path):
    """If LLM fails, endpoint returns 200 with unchanged accordion."""
    subs_dir = Path("midias/testuser/subtitles")
    subs_dir.mkdir(parents=True, exist_ok=True)
    subs_file = subs_dir / "failtest.txt"
    subs_file.write_text("[00:00:01] test\n", encoding="utf-8")

    auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "youtube",
            "name": "Fail Video",
            "url": "https://www.youtube.com/watch?v=failtest",
            "image_path": "",
        },
    )

    with patch("app.main.classify_transcript", return_value=None):
        response = auth_client.post("/htmx/library/1/classify")

    assert response.status_code == 200

    subs_file.unlink(missing_ok=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_classify.py -v`
Expected: FAIL — `ImportError` or 404 because the endpoint doesn't exist yet.

- [ ] **Step 3: Add imports to main.py**

Add these imports at the top of `app/main.py`, after the existing imports:

```python
import logging
from app.services.llm_classifier import classify_transcript
from app.services.taxonomy_service import get_taxonomy_for_subject
from app.services.tree_builder import build_tree_for_subject, rebuild_content_json
from app.services.url_builder import build_step_url
```

And add a logger near the top:

```python
logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Modify the save endpoint response for YouTube items**

In `app/main.py`, in the `htmx_library_save` function, modify the response section (around lines 929-935). Replace the current response building with:

```python
    response = templates.TemplateResponse(
        request=request,
        name="partials/library_item.html",
        context=_ctx(request, {
            "item": item,
            "trigger_classify": type == "youtube" and subtitle_path is not None,
            "classify_item_id": cursor.lastrowid,
            "classify_subject_id": subject_id,
        }),
    )
    response.headers["HX-Trigger"] = "close-add-modal"
    return response
```

- [ ] **Step 5: Add the classify endpoint**

Add this endpoint to `app/main.py`, before the `# --- Public HTMX routes ---` comment:

```python
@app.post("/htmx/library/{item_id}/classify")
async def htmx_library_classify(
    item_id: int,
    request: Request,
    user=Depends(require_auth),
    db=Depends(get_db),
):
    # Fetch the library item and verify ownership
    cursor = await db.execute(
        """
        SELECT li.id, li.subtitle_path, li.subject_id, li.url
        FROM library_items li
        JOIN subjects s ON li.subject_id = s.id
        WHERE li.id = ? AND s.owner_id = ?
        """,
        (item_id, user["id"]),
    )
    item = await cursor.fetchone()
    if not item:
        raise HTTPException(status_code=404)

    subject_id = item["subject_id"]
    subtitle_path = item["subtitle_path"]

    # If no subtitle_path, return current accordion unchanged
    if not subtitle_path:
        topics = parse_topics_json(
            (await (await db.execute("SELECT content_json FROM subjects WHERE id = ?", (subject_id,))).fetchone())["content_json"]
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/topics_accordion.html",
            context=_ctx(request, {"topics": topics}),
        )

    # Read the subtitle file
    subs_file = Path("midias") / subtitle_path
    if not subs_file.exists():
        logger.error("Subtitle file not found: %s", subs_file)
        topics = parse_topics_json(
            (await (await db.execute("SELECT content_json FROM subjects WHERE id = ?", (subject_id,))).fetchone())["content_json"]
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/topics_accordion.html",
            context=_ctx(request, {"topics": topics}),
        )

    transcript = subs_file.read_text(encoding="utf-8").strip()

    # Get existing taxonomy for this subject
    taxonomy = await get_taxonomy_for_subject(db, subject_id)

    # Call LLM in a thread (blocking call)
    result = await asyncio.to_thread(classify_transcript, taxonomy, transcript)

    if result is not None:
        # Extract youtube_id from URL
        video_url = item["url"] or ""
        m = YOUTUBE_RE.search(video_url)
        youtube_id = m.group(1) if m else ""

        # Delete old knowledge_items for this library_id (for reprocessing)
        await db.execute("DELETE FROM knowledge_items WHERE library_id = ?", (item_id,))

        # Insert new knowledge_items
        for ki in result.itens:
            url = build_step_url(youtube_id, ki.timestamp) if youtube_id else None
            await db.execute(
                """INSERT INTO knowledge_items
                   (library_id, topico, subtopico, acao, timestamp, pagina, trecho_referencia, file_path, url)
                   VALUES (?, ?, ?, ?, ?, NULL, '', NULL, ?)""",
                (item_id, ki.topico, ki.subtopico, ki.acao, ki.timestamp, url),
            )

        # Mark as processed
        await db.execute(
            "UPDATE library_items SET processed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (item_id,),
        )

        # Rebuild the content_json for the subject
        await rebuild_content_json(db, subject_id)
    else:
        logger.warning("LLM classification failed for library_item %d", item_id)

    # Return updated accordion
    row = await db.execute("SELECT content_json FROM subjects WHERE id = ?", (subject_id,))
    subject_row = await row.fetchone()
    topics = parse_topics_json(subject_row["content_json"] if subject_row else None)

    return templates.TemplateResponse(
        request=request,
        name="partials/topics_accordion.html",
        context=_ctx(request, {"topics": topics}),
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_classify.py -v`
Expected: Tests may fail due to missing template. That's expected — we'll create it in the next task.

- [ ] **Step 7: Commit**

```bash
git add app/main.py tests/test_classify.py
git commit -m "feat: add classify endpoint and modify save to trigger classification"
```

---

### Task 8: Templates — Accordion Partial, Classify Trigger, Spinner

**Files:**
- Create: `app/templates/partials/topics_accordion.html`
- Modify: `app/templates/topics.html:177-241` (extract accordion into partial, add spinner, add id)
- Modify: `app/templates/partials/library_item.html` (add classify trigger div)

- [ ] **Step 1: Create the accordion partial**

Create `app/templates/partials/topics_accordion.html`:

```html
{% for topico in topics %}
<!-- Level 1: Tópico -->
<div x-data="{ open: false }" class="bg-white dark:bg-neutral-800 rounded-xl border border-slate-200 dark:border-neutral-700 overflow-hidden">
  <button @click="open = !open" class="w-full flex items-center justify-between px-5 py-4 text-left cursor-pointer hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors">
    <span class="text-base font-bold text-slate-700 dark:text-neutral-300">{{ topico.titulo }}</span>
    <svg class="w-5 h-5 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
    </svg>
  </button>

  <div x-show="open" x-collapse>
    {% for subtopico in topico.subtopicos %}
    <!-- Level 2: Subtópico -->
    <div x-data="{ open: false }" class="border-t border-slate-100 dark:border-neutral-700 bg-slate-100 dark:bg-[#1e1e1e]">
      <button @click="open = !open" class="w-full flex items-center justify-between pl-10 pr-5 py-3 text-left cursor-pointer hover:bg-slate-100 dark:hover:bg-neutral-700 transition-colors">
        <span class="text-sm font-semibold text-slate-700 dark:text-neutral-300">{{ subtopico.titulo }}</span>
        <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>

      <div x-show="open" x-collapse>
        {% for passo in subtopico.passos %}
        <!-- Level 3: Passo -->
        <button
          @click="$dispatch('open-library-modal', {
            type: '{{ 'video' if passo.url else 'pdf' }}',
            url: '{{ passo.url or passo.file_path or '' }}',
            name: '{{ passo.acao | e }}',
            timestamp: '{{ passo.timestamp or '' }}',
            page: {{ passo.pagina or 'null' }}
          })"
          class="w-full text-left pl-16 pr-5 py-2.5 text-sm text-[#26a69a] dark:text-teal-400 bg-slate-200 dark:bg-[#181818] hover:bg-slate-300 dark:hover:bg-neutral-700 transition-colors cursor-pointer"
        >
          <div class="flex items-center gap-2">
            {% if passo.url %}
            <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            {% elif passo.file_path %}
            <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            {% else %}
            <svg class="w-4 h-4 flex-shrink-0 text-slate-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
            </svg>
            {% endif %}
            {{ passo.acao }}
          </div>
          {% if passo.trecho_referencia %}
          <p class="pl-6 mt-0.5 text-xs text-slate-400 dark:text-neutral-500">{{ passo.trecho_referencia }}</p>
          {% endif %}
        </button>
        {% endfor %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>
{% endfor %}
```

- [ ] **Step 2: Modify topics.html to use the partial and add spinner**

In `app/templates/topics.html`, replace lines 177-241 (the `<div class="space-y-3">` block containing the accordion + closing `</main>` and `</div>`) with:

```html
    <!-- Classify spinner (shown during LLM processing) -->
    <div id="classify-spinner" class="htmx-indicator flex items-center justify-center gap-3 py-6">
      <div class="w-8 h-8 border-4 border-teal-500/20 border-t-teal-500 rounded-full animate-spin"></div>
      <span class="text-sm text-teal-500 dark:text-teal-400 font-medium">Fazendo a Mágica Acontecer...</span>
    </div>

    <div id="topics-accordion" class="space-y-3">
      {% include "partials/topics_accordion.html" %}
    </div>
  </main>

</div>
```

- [ ] **Step 3: Modify library_item.html to include classify trigger**

At the end of `app/templates/partials/library_item.html`, just before the closing `</div>` (the outermost group div), add:

```html
{% if trigger_classify %}
<div hx-post="/htmx/library/{{ classify_item_id }}/classify"
     hx-trigger="load"
     hx-target="#topics-accordion"
     hx-swap="innerHTML"
     hx-indicator="#classify-spinner"
     style="display:none">
</div>
{% endif %}
```

- [ ] **Step 4: Run all tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS (including the classify tests that previously needed the template).

- [ ] **Step 5: Commit**

```bash
git add app/templates/partials/topics_accordion.html app/templates/topics.html app/templates/partials/library_item.html
git commit -m "feat: add accordion partial, classify spinner, and auto-trigger"
```

---

### Task 9: Integration Test — Full Flow

**Files:**
- Create: `tests/test_classify_integration.py`

- [ ] **Step 1: Write the integration test**

Create `tests/test_classify_integration.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch

from app.schemas.llm_output import ResultadoLLM


def test_save_youtube_triggers_classify_div(auth_client):
    """After saving a YouTube item, the response includes the classify trigger div."""
    response = auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "youtube",
            "name": "My Video",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "image_path": "testuser/thumbnails/fake.jpg",
        },
    )
    assert response.status_code == 200
    assert "hx-post" in response.text
    assert "/classify" in response.text


def test_save_pdf_does_not_trigger_classify(auth_client):
    """After saving a PDF item, no classify trigger is included."""
    response = auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "pdf",
            "name": "My PDF",
            "file_path": "testuser/pdfs/fake.pdf",
            "image_path": "testuser/thumbnails/fake.jpg",
        },
    )
    assert response.status_code == 200
    assert "/classify" not in response.text


def test_full_classify_updates_content_json(auth_client):
    """Classify endpoint persists knowledge_items and updates content_json."""
    # Create subtitle file
    subs_dir = Path("midias/testuser/subtitles")
    subs_dir.mkdir(parents=True, exist_ok=True)
    subs_file = subs_dir / "integtest.txt"
    subs_file.write_text("[00:00:07] selecionar o arquivo\n", encoding="utf-8")

    # Save item
    auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "youtube",
            "name": "Integration Test",
            "url": "https://www.youtube.com/watch?v=integtest",
            "image_path": "",
        },
    )

    # Mock LLM and classify
    mock_result = ResultadoLLM(**{
        "itens": [
            {"topico": "Setup", "subtopico": "Inicial", "acao": "Selecionar arquivo", "timestamp": "00:00:07"},
        ]
    })

    with patch("app.main.classify_transcript", return_value=mock_result):
        response = auth_client.post("/htmx/library/1/classify")

    assert response.status_code == 200
    # The response should contain the accordion HTML with the new topic
    assert "Setup" in response.text
    assert "Selecionar arquivo" in response.text

    subs_file.unlink(missing_ok=True)
```

- [ ] **Step 2: Run the integration test**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/test_classify_integration.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 3: Run the full test suite**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_classify_integration.py
git commit -m "test: add integration tests for classify flow"
```

---

### Task 10: Manual Verification

**Files:** None (verification only)

- [ ] **Step 1: Start the dev server**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`
Expected: Server starts on :8000

- [ ] **Step 2: Verify the migration ran**

Run: `cd /home/ubuntu/aaaa/easy-boiler && sqlite3 data/app.db "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_items'"`
Expected: `knowledge_items`

- [ ] **Step 3: Test the full flow in the browser**

1. Navigate to a subject page
2. Open the library drawer
3. Add a YouTube video via the modal
4. Observe: spinner shows "Baixando metadados e legendas..." during Apify
5. Modal closes, item appears in library
6. Observe: spinner shows "Fazendo a Mágica Acontecer..." over the accordion area
7. Accordion updates with new topics from the LLM classification

- [ ] **Step 4: Verify data in the database**

Run: `cd /home/ubuntu/aaaa/easy-boiler && sqlite3 data/app.db "SELECT id, topico, subtopico, acao, timestamp, url FROM knowledge_items LIMIT 10"`
Expected: Rows with topic/subtopic/action data, timestamps, and YouTube URLs with `&t=Ns` parameter.

Run: `cd /home/ubuntu/aaaa/easy-boiler && sqlite3 data/app.db "SELECT id, processed_at FROM library_items WHERE processed_at IS NOT NULL"`
Expected: The processed item shows a timestamp.
