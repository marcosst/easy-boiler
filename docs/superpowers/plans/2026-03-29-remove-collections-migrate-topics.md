# Remove Collections & Migrate Topics to Markdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the collections layer, store topics as markdown in the projects table, add library_items table, and update routes to `/{username}/{shortname}`.

**Architecture:** Single markdown field (`content_md`) on `projects` replaces all mock topic data. A parser function extracts heading hierarchy into a structure the accordion template consumes. New `library_items` table stores source materials (schema only, no UI yet).

**Tech Stack:** FastAPI, aiosqlite, Jinja2, HTMX, Python `markdown` lib, dbmate migrations, pytest

---

### Task 1: Create the markdown parser module

**Files:**
- Create: `app/md_parser.py`
- Create: `tests/test_md_parser.py`

- [ ] **Step 1: Write failing tests for `parse_topics_md`**

Create `tests/test_md_parser.py`:

```python
from app.md_parser import parse_topics_md


def test_parse_empty_returns_empty_list():
    assert parse_topics_md("") == []
    assert parse_topics_md(None) == []


def test_parse_single_topic():
    md = "# Introdução"
    result = parse_topics_md(md)
    assert len(result) == 1
    assert result[0]["title"] == "Introdução"
    assert result[0]["id"] == "1"
    assert result[0]["subtopics"] == []


def test_parse_full_hierarchy():
    md = """# Tópico 1
## Subtópico 1.1
### Detalhe 1.1.1
Conteúdo do detalhe.
### Detalhe 1.1.2
## Subtópico 1.2
### Detalhe 1.2.1
Mais conteúdo aqui.

Com múltiplas linhas.
# Tópico 2
## Subtópico 2.1
### Detalhe 2.1.1"""
    result = parse_topics_md(md)
    assert len(result) == 2

    t1 = result[0]
    assert t1["title"] == "Tópico 1"
    assert t1["id"] == "1"
    assert len(t1["subtopics"]) == 2

    s1 = t1["subtopics"][0]
    assert s1["title"] == "Subtópico 1.1"
    assert s1["id"] == "1.1"
    assert len(s1["details"]) == 2

    d1 = s1["details"][0]
    assert d1["title"] == "Detalhe 1.1.1"
    assert d1["id"] == "1.1.1"
    assert d1["content_md"] == "Conteúdo do detalhe."
    assert d1["has_content"] is True

    d2 = s1["details"][1]
    assert d2["title"] == "Detalhe 1.1.2"
    assert d2["has_content"] is False

    s2 = t1["subtopics"][1]
    assert s2["id"] == "1.2"
    d_1_2_1 = s2["details"][0]
    assert d_1_2_1["content_md"] == "Mais conteúdo aqui.\n\nCom múltiplas linhas."
    assert d_1_2_1["has_content"] is True

    t2 = result[1]
    assert t2["id"] == "2"
    assert t2["subtopics"][0]["id"] == "2.1"
    assert t2["subtopics"][0]["details"][0]["id"] == "2.1.1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_md_parser.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement `parse_topics_md`**

Create `app/md_parser.py`:

```python
def parse_topics_md(content_md: str | None) -> list:
    """Parse markdown with # / ## / ### headings into a topic hierarchy."""
    if not content_md:
        return []

    topics = []
    current_topic = None
    current_subtopic = None
    current_detail = None
    detail_lines = []

    topic_counter = 0
    subtopic_counter = 0
    detail_counter = 0

    def _flush_detail():
        nonlocal detail_lines, current_detail
        if current_detail is not None:
            content = "\n".join(detail_lines).strip()
            current_detail["content_md"] = content if content else ""
            current_detail["has_content"] = bool(content)
            detail_lines = []

    for line in content_md.split("\n"):
        stripped = line.strip()

        if stripped.startswith("### "):
            _flush_detail()
            detail_counter += 1
            current_detail = {
                "title": stripped[4:].strip(),
                "id": f"{topic_counter}.{subtopic_counter}.{detail_counter}",
                "content_md": "",
                "has_content": False,
            }
            if current_subtopic is not None:
                current_subtopic["details"].append(current_detail)
            detail_lines = []

        elif stripped.startswith("## "):
            _flush_detail()
            subtopic_counter += 1
            detail_counter = 0
            current_detail = None
            current_subtopic = {
                "title": stripped[3:].strip(),
                "id": f"{topic_counter}.{subtopic_counter}",
                "details": [],
            }
            if current_topic is not None:
                current_topic["subtopics"].append(current_subtopic)

        elif stripped.startswith("# "):
            _flush_detail()
            topic_counter += 1
            subtopic_counter = 0
            detail_counter = 0
            current_detail = None
            current_subtopic = None
            current_topic = {
                "title": stripped[2:].strip(),
                "id": str(topic_counter),
                "subtopics": [],
            }
            topics.append(current_topic)

        else:
            if current_detail is not None:
                detail_lines.append(line)

    _flush_detail()
    return topics


def get_detail_content(content_md: str | None, detail_id: str) -> str | None:
    """Return the content_md of a specific detail by its hierarchical id."""
    topics = parse_topics_md(content_md)
    for topic in topics:
        for subtopic in topic["subtopics"]:
            for detail in subtopic["details"]:
                if detail["id"] == detail_id and detail["has_content"]:
                    return detail["content_md"]
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_md_parser.py -v`
Expected: All PASS

- [ ] **Step 5: Write failing tests for `get_detail_content`**

Add to `tests/test_md_parser.py`:

```python
from app.md_parser import get_detail_content


def test_get_detail_content_found():
    md = "# T\n## S\n### D\nHello world."
    result = get_detail_content(md, "1.1.1")
    assert result == "Hello world."


def test_get_detail_content_not_found():
    md = "# T\n## S\n### D\nHello."
    assert get_detail_content(md, "9.9.9") is None


def test_get_detail_content_empty_md():
    assert get_detail_content(None, "1.1.1") is None
    assert get_detail_content("", "1.1.1") is None
```

- [ ] **Step 6: Run tests to verify they pass (already implemented)**

Run: `python -m pytest tests/test_md_parser.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add app/md_parser.py tests/test_md_parser.py
git commit -m "feat: add markdown parser for topic hierarchy"
```

---

### Task 2: Database migration — add content_md and library_items

**Files:**
- Create: `db/migrations/YYYYMMDDHHMMSS_add_content_md_and_library_items.sql`

- [ ] **Step 1: Create the migration file**

Run: `make db-new name=add_content_md_and_library_items`

Then replace the generated file contents with:

```sql
-- migrate:up
ALTER TABLE projects ADD COLUMN content_md TEXT;

CREATE TABLE library_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('video', 'pdf', 'document', 'other')),
    url TEXT,
    file_path TEXT,
    image_path TEXT,
    subtitle_path TEXT,
    metadata TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_library_items_project ON library_items(project_id);

-- Seed content_md for existing projects
UPDATE projects SET content_md = '# Introdução
## Visão Geral
### Resumo do tema
Este é um conteúdo de exemplo em **markdown**.

- Ponto importante 1
- Ponto importante 2
- Ponto importante 3
### Material complementar
## Contexto Histórico
### Linha do tempo
Texto sobre a história do tema.
# Conceitos Fundamentais
## Definições
### Glossário de termos
Lista de termos e definições relevantes.
### Diagrama conceitual
## Princípios
### Princípio 1
Descrição do primeiro princípio fundamental.
# Aplicações Práticas
## Estudo de Caso
### Exemplo resolvido
Passo a passo de um problema resolvido.

Com detalhes adicionais.
### Exercício proposto
## Exercícios
### Exercício 1
Resolva o problema aplicando os conceitos aprendidos.'
WHERE content_md IS NULL;

-- migrate:down
DROP INDEX IF EXISTS idx_library_items_project;
DROP TABLE IF EXISTS library_items;

-- SQLite does not support DROP COLUMN before 3.35.0; recreate table if needed.
-- For simplicity, just leave the column (it will be ignored).
```

- [ ] **Step 2: Run the migration**

Run: `make migrate`
Expected: Migration applied successfully

- [ ] **Step 3: Commit**

```bash
git add db/migrations/ db/schema.sql
git commit -m "feat: add content_md to projects and create library_items table"
```

---

### Task 3: Update test fixtures — add content_md to schema and seed

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Update the SCHEMA and seed data in conftest.py**

In `tests/conftest.py`, update the `SCHEMA` string to add `content_md TEXT` to the projects table:

```python
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
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    shortname TEXT NOT NULL UNIQUE
                     CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    image_path TEXT,
    content_md TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE library_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('video', 'pdf', 'document', 'other')),
    url TEXT,
    file_path TEXT,
    image_path TEXT,
    subtitle_path TEXT,
    metadata TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_library_items_project ON library_items(project_id);
"""
```

Add a constant for test markdown content after the SCHEMA:

```python
TEST_CONTENT_MD = """# Introdução
## Visão Geral
### Resumo do tema
Este é um conteúdo de exemplo em **markdown**.
### Material complementar
## Contexto Histórico
### Linha do tempo
Texto sobre a história do tema.
# Conceitos Fundamentais
## Definições
### Glossário de termos
Lista de termos e definições relevantes.
# Aplicações Práticas
## Estudo de Caso
### Exemplo resolvido
Passo a passo de um problema resolvido."""
```

Update the project INSERT statements in `setup_db` to include `content_md`:

```python
await db.execute(
    "INSERT INTO projects (name, shortname, owner_id, content_md) VALUES (?, ?, ?, ?)",
    ("Projeto Teste", "projeto-teste", 1, TEST_CONTENT_MD),
)
await db.execute(
    "INSERT INTO projects (name, shortname, owner_id, content_md) VALUES (?, ?, ?, ?)",
    ("Segundo Projeto", "segundo-projeto", 1, TEST_CONTENT_MD),
)
```

- [ ] **Step 2: Run existing tests to verify fixtures work**

Run: `python -m pytest tests/test_home.py -v`
Expected: All PASS (home tests don't depend on collections)

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add content_md and library_items to test schema"
```

---

### Task 4: Remove collections mock data and old routes from main.py

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Remove mock data constants and functions**

In `app/main.py`, delete these blocks entirely:
- `MOCK_PROJECTS` (lines 37-44)
- `_COLLECTION_COLORS` (lines 46-53)
- `MOCK_COLLECTIONS` (lines 55-66)
- `_build_mock_topics()` function (lines 69-143)
- `MOCK_TOPICS, MOCK_DETAILS = _build_mock_topics()` (line 146)
- `_collect_content_details()` function (lines 389-413)

- [ ] **Step 2: Remove old routes**

Delete these routes from `app/main.py`:
- `project_topics` route at `GET /projects/{project_id}` (lines 416-432)
- `topics` route at `GET /projects/{project_id}/collections/{collection_id}` (lines 435-455)
- `htmx_detail` route at `GET /htmx/details/{detail_id}` (lines 478-496)

- [ ] **Step 3: Add imports for the new parser and markdown**

At the top of `app/main.py`, add:

```python
import re

from app.md_parser import get_detail_content, parse_topics_md
```

The `import markdown as md` is already present.

- [ ] **Step 4: Add the new `/{username}/{shortname}` route**

Add after the `user_projects` route:

```python
@app.get("/{username}/{shortname}")
async def project_topics(request: Request, username: str, shortname: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute(
        """
        SELECT p.id, p.name, p.shortname, p.content_md, p.image_path
        FROM projects p
        JOIN users u ON p.owner_id = u.id
        WHERE u.username = ? AND p.shortname = ?
        """,
        (username, shortname),
    )
    project = await row.fetchone()
    if not project:
        raise HTTPException(status_code=404)
    topics = parse_topics_md(project["content_md"])
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context={
            "user": user,
            "project": project,
            "topics": topics,
            "username": username,
            "shortname": shortname,
        },
    )
```

- [ ] **Step 5: Add the new HTMX detail route**

Add after the new project_topics route:

```python
YOUTUBE_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)"
)


@app.get("/htmx/details/{username}/{shortname}/{detail_id}")
async def htmx_detail(request: Request, username: str, shortname: str, detail_id: str, db=Depends(get_db)):
    row = await db.execute(
        """
        SELECT p.content_md
        FROM projects p
        JOIN users u ON p.owner_id = u.id
        WHERE u.username = ? AND p.shortname = ?
        """,
        (username, shortname),
    )
    project = await row.fetchone()
    if not project:
        raise HTTPException(status_code=404)
    content = get_detail_content(project["content_md"], detail_id)
    if content is None:
        raise HTTPException(status_code=404)
    content_html = md.markdown(content)
    # Convert YouTube links to embeds
    def _youtube_embed(match):
        vid = match.group(1)
        return (
            f'<div class="aspect-video rounded-xl overflow-hidden mb-4 bg-black">'
            f'<iframe src="https://www.youtube.com/embed/{vid}" class="w-full h-full" '
            f'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
            f'gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
        )
    content_html = YOUTUBE_RE.sub(_youtube_embed, content_html)
    return templates.TemplateResponse(
        request=request,
        name="partials/detail_modal.html",
        context={"detail": {"content_html": content_html}},
    )
```

- [ ] **Step 6: Verify the app starts without import errors**

Run: `python -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add app/main.py
git commit -m "feat: replace collections with markdown-based topics and new routes"
```

---

### Task 5: Update templates

**Files:**
- Delete: `app/templates/collections.html`
- Modify: `app/templates/topics.html`
- Modify: `app/templates/partials/detail_modal.html`

- [ ] **Step 1: Delete collections.html**

```bash
rm app/templates/collections.html
```

- [ ] **Step 2: Update topics.html — accordion to use parsed data**

In `app/templates/topics.html`, update the accordion section (the `<div class="space-y-3">` block starting at line 200) to use the new data structure. Replace the detail `hx-get` URLs:

Change every occurrence of:
```
hx-get="/htmx/details/{{ detail.id }}"
```
to:
```
hx-get="/htmx/details/{{ username }}/{{ shortname }}/{{ detail.id }}"
```

The drawer items also need updated URLs. In the drawer section, replace:
```
hx-get="/htmx/details/{{ item.id }}"
```
with:
```
hx-get="/htmx/details/{{ username }}/{{ shortname }}/{{ item.id }}"
```

The accordion structure itself stays the same since the template already iterates `topics` → `topic.subtopics` → `subtopic.details` and checks `detail.has_content`. The field names (`name` vs `title`) need updating:

Replace in the accordion:
- `{{ topic.name }}` → `{{ topic.title }}`
- `{{ subtopic.name }}` → `{{ subtopic.title }}`
- `{{ detail.name }}` → `{{ detail.title }}`

Remove the `drawer_items` drawer section entirely (lines 74-168 in topics.html — the `<!-- Side Drawer -->` aside block), and the drawer toggle button in the main content. The library drawer will be re-implemented when the library UI is built.

Also remove the `drawerOpen` variable from the `x-data` on line 10 and the `:class="{ 'mr-80': drawerOpen, ... }"` on the main element. Keep `chatOpen` and the chat drawer.

Update line 10 from:
```html
<div x-data="{ drawerOpen: false, chatOpen: false, chatMessages: [], chatInput: '' }" x-init="chatMessages = [{ role: 'assistant', text: 'Olá! Sou seu assistente de estudos. Pergunte qualquer coisa sobre este projeto.' }]">
```
to:
```html
<div x-data="{ chatOpen: false, chatMessages: [], chatInput: '' }" x-init="chatMessages = [{ role: 'assistant', text: 'Olá! Sou seu assistente de estudos. Pergunte qualquer coisa sobre este projeto.' }]">
```

Update line 171 from:
```html
<main class="max-w-7xl mx-auto px-6 py-8" :class="{ 'mr-80': drawerOpen, 'mr-[28rem]': chatOpen }" style="transition: margin 0.3s ease;">
```
to:
```html
<main class="max-w-7xl mx-auto px-6 py-8" :class="{ 'mr-[28rem]': chatOpen }" style="transition: margin 0.3s ease;">
```

In the buttons div (line 173-197), remove the library button (`x-show="!drawerOpen && !chatOpen"` with "Biblioteca" text) and update the chat button to remove `drawerOpen` references:

Replace:
```html
<button
  x-show="!drawerOpen && !chatOpen"
  @click="drawerOpen = false; chatOpen = true"
```
with:
```html
<button
  x-show="!chatOpen"
  @click="chatOpen = true"
```

- [ ] **Step 3: Update detail_modal.html — simplified**

Replace `app/templates/partials/detail_modal.html` contents with:

```html
<div class="p-6">
  {% if detail.content_html %}
  <div class="prose prose-sm dark:prose-invert max-w-none text-slate-700 dark:text-neutral-300">
    {{ detail.content_html | safe }}
  </div>
  {% endif %}
</div>
```

The YouTube embed is now handled by the backend (converted inline in the markdown HTML), so the separate `youtube_url` iframe block is no longer needed.

- [ ] **Step 4: Commit**

```bash
git add -A app/templates/
git commit -m "feat: update templates — remove collections, use markdown-based topics"
```

---

### Task 6: Rewrite tests

**Files:**
- Delete: `tests/test_collections.py`
- Modify: `tests/test_topics.py`
- Modify: `tests/test_dark_mode.py`

- [ ] **Step 1: Delete test_collections.py**

```bash
rm tests/test_collections.py
```

- [ ] **Step 2: Rewrite test_topics.py**

Replace `tests/test_topics.py` with:

```python
def test_project_topics_returns_200(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert response.status_code == 200


def test_project_topics_shows_project_name(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "Projeto Teste" in response.text


def test_project_topics_has_home_link(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert 'href="/"' in response.text


def test_project_topics_shows_accordion_structure(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "Introdução" in response.text
    assert "Conceitos Fundamentais" in response.text
    assert "Aplicações Práticas" in response.text


def test_project_topics_has_alpine_accordion(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "x-data" in response.text
    assert "x-show" in response.text


def test_project_topics_has_dark_mode_classes(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "dark:bg-neutral-900" in response.text
    assert "dark:bg-neutral-800" in response.text


def test_project_topics_detail_is_clickable(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "hx-get" in response.text
    assert "/htmx/details/testuser/projeto-teste/" in response.text


def test_project_topics_unknown_project_returns_404(auth_client):
    response = auth_client.get("/testuser/nonexistent")
    assert response.status_code == 404


def test_project_topics_unknown_user_returns_404(auth_client):
    response = auth_client.get("/nobody/projeto-teste")
    assert response.status_code == 404


def test_htmx_detail_returns_200(auth_client):
    response = auth_client.get("/htmx/details/testuser/projeto-teste/1.1.1")
    assert response.status_code == 200


def test_htmx_detail_invalid_returns_404(auth_client):
    response = auth_client.get("/htmx/details/testuser/projeto-teste/9.9.9")
    assert response.status_code == 404


def test_htmx_detail_renders_markdown_html(auth_client):
    response = auth_client.get("/htmx/details/testuser/projeto-teste/1.1.1")
    assert "<strong>" in response.text or "<em>" in response.text
```

- [ ] **Step 3: Update test_dark_mode.py — remove collection tests**

Remove these two tests from `tests/test_dark_mode.py`:
- `test_collections_cards_have_dark_classes` (lines 35-38)
- `test_collections_section_title_has_dark_class` (lines 46-48)

Add replacements for the topics page:

```python
def test_topics_cards_have_dark_classes(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "dark:bg-neutral-800" in response.text
    assert "dark:border-neutral-700" in response.text


def test_topics_section_title_has_dark_class(auth_client):
    response = auth_client.get("/testuser/projeto-teste")
    assert "dark:text-neutral-100" in response.text
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add -A tests/
git commit -m "test: rewrite tests for markdown-based topics, remove collection tests"
```

---

### Task 7: Final cleanup and verification

**Files:**
- Verify: `app/main.py` (no remaining collection references)

- [ ] **Step 1: Search for any remaining collection references**

Run: `grep -ri "collection" app/ tests/ --include="*.py" --include="*.html"`
Expected: No results (or only harmless SQL COLLATE references in database.py)

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest -v`
Expected: All PASS

- [ ] **Step 3: Start the dev server and verify manually**

Run: `make dev` (quick manual check that the app starts without errors)
Expected: Uvicorn starts on port 8000

- [ ] **Step 4: Commit any remaining cleanup**

If any stray references were found and fixed:

```bash
git add -A
git commit -m "chore: final cleanup of collection references"
```
