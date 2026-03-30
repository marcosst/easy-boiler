# Library Add Modal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to add YouTube videos and PDFs to a subject's library via a modal with auto-preview (thumbnail + title).

**Architecture:** New dbmate migration restricts `library_items.type` to `youtube`/`pdf`. Two new HTMX endpoints handle preview (fetch metadata + generate thumbnail) and save. The modal lives in a new partial, uses Alpine.js for state and HTMX for server calls.

**Tech Stack:** FastAPI, HTMX, Alpine.js, Tailwind, httpx (oEmbed + thumbnail download), PyMuPDF (PDF thumbnail), aiosqlite.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `db/migrations/20260331000000_library_type_constraint.sql` | Migration: restrict type to `youtube`/`pdf` |
| Modify | `pyproject.toml` | Add `httpx`, `pymupdf` to main deps |
| Modify | `tests/conftest.py` | Update test schema to match current DB (content_json + new type constraint) |
| Create | `tests/test_library.py` | Tests for preview + save endpoints |
| Modify | `app/main.py:501-551` | Add preview + save endpoints, update topics route thumbnail logic |
| Create | `app/templates/partials/library_add_modal.html` | Modal with type selector, input, HTMX preview target |
| Create | `app/templates/partials/library_preview.html` | Preview fragment (thumbnail + editable name + save button) |
| Create | `app/templates/partials/library_item.html` | Single library item card (extracted from topics.html) |
| Modify | `app/templates/topics.html:84-178` | Wire "+" button to modal, use library_item partial |
| Modify | `scripts/seed.py:43-110` | Change `type: "video"` to `type: "youtube"` |

---

### Task 1: Database Migration

**Files:**
- Create: `db/migrations/20260331000000_library_type_constraint.sql`

- [ ] **Step 1: Create migration file**

```sql
-- migrate:up

CREATE TABLE library_items_new (
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
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO library_items_new (id, subject_id, name, type, url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at)
SELECT id, subject_id, name,
       CASE WHEN type = 'video' THEN 'youtube' ELSE type END,
       url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at
FROM library_items;

DROP TABLE library_items;
ALTER TABLE library_items_new RENAME TO library_items;

CREATE INDEX idx_library_items_subject ON library_items(subject_id);

-- migrate:down

CREATE TABLE library_items_old (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id    INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    type          TEXT    NOT NULL CHECK(type IN ('video', 'pdf', 'document', 'other')),
    url           TEXT,
    file_path     TEXT,
    image_path    TEXT,
    subtitle_path TEXT,
    metadata      TEXT,
    position      INTEGER NOT NULL DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO library_items_old (id, subject_id, name, type, url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at)
SELECT id, subject_id, name,
       CASE WHEN type = 'youtube' THEN 'video' ELSE type END,
       url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at
FROM library_items;

DROP TABLE library_items;
ALTER TABLE library_items_old RENAME TO library_items;

CREATE INDEX idx_library_items_subject ON library_items(subject_id);
```

- [ ] **Step 2: Run migration**

Run: `make migrate`
Expected: Migration applies successfully. `db/schema.sql` updates to show `CHECK(type IN ('youtube', 'pdf'))`.

- [ ] **Step 3: Update seed script**

In `scripts/seed.py`, replace every `"type": "video"` with `"type": "youtube"`. There are 16 occurrences across the subjects_data list.

- [ ] **Step 4: Commit**

```bash
git add db/migrations/20260331000000_library_type_constraint.sql db/schema.sql scripts/seed.py
git commit -m "feat: restrict library_items type to youtube/pdf"
```

---

### Task 2: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add httpx and pymupdf to main dependencies**

In `pyproject.toml`, add to the `dependencies` list:

```toml
dependencies = [
    "aiosqlite",
    "authlib",
    "fastapi",
    "httpx>=0.27",
    "jinja2",
    "passlib[bcrypt]",
    "pymupdf>=1.25",
    "python-dotenv",
    "yt-dlp",
    "uvicorn[standard]",
    "youtube-transcript-api",
    "itsdangerous>=2.2.0",
    "python-multipart>=0.0.22",
]
```

Also remove `httpx` from dev dependencies since it's now a main dep:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

- [ ] **Step 2: Sync dependencies**

Run: `uv sync`
Expected: Both `httpx` and `pymupdf` install successfully.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add httpx and pymupdf dependencies"
```

---

### Task 3: Update Test Schema & Write Tests

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/test_library.py`

- [ ] **Step 1: Update conftest schema to match current DB**

The test schema in `tests/conftest.py` is outdated — it still has `content_md` and the old type constraint. Replace the `SCHEMA` string and fixture setup:

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
CREATE TABLE subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    shortname TEXT NOT NULL UNIQUE
                     CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    image_path TEXT,
    content_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_subjects_owner ON subjects(owner_id);
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
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_library_items_subject ON library_items(subject_id);
"""
```

Also update the fixture insert to use `content_json` instead of `content_md`:

```python
TEST_CONTENT_JSON = json.dumps({
    "topicos": [{
        "titulo": "Introducao",
        "subtopicos": [{
            "titulo": "Visao Geral",
            "passos": [{"acao": "Exemplo", "timestamp": None, "pagina": None, "trecho_referencia": "", "file_path": None, "url": None}]
        }]
    }]
})
```

Replace the two subject inserts in `setup_db()`:

```python
await db.execute(
    "INSERT INTO subjects (name, shortname, owner_id, content_json) VALUES (?, ?, ?, ?)",
    ("Assunto Teste", "assunto-teste", 1, TEST_CONTENT_JSON),
)
await db.execute(
    "INSERT INTO subjects (name, shortname, owner_id, content_json) VALUES (?, ?, ?, ?)",
    ("Segundo Assunto", "segundo-assunto", 1, TEST_CONTENT_JSON),
)
```

Add `import json` at the top of conftest.py.

- [ ] **Step 2: Write test file for library endpoints**

Create `tests/test_library.py`:

```python
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient


def test_preview_youtube_returns_preview(auth_client, tmp_path):
    """POST /htmx/library/preview with type=youtube returns preview HTML."""
    mock_oembed_response = MagicMock()
    mock_oembed_response.status_code = 200
    mock_oembed_response.json.return_value = {"title": "Test Video Title"}
    mock_oembed_response.raise_for_status = MagicMock()

    mock_thumb_response = MagicMock()
    mock_thumb_response.status_code = 200
    mock_thumb_response.content = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
    mock_thumb_response.raise_for_status = MagicMock()

    with patch("httpx.get") as mock_get:
        mock_get.side_effect = [mock_oembed_response, mock_thumb_response]
        response = auth_client.post(
            "/htmx/library/preview",
            data={
                "type": "youtube",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "subject_id": "1",
            },
        )

    assert response.status_code == 200
    assert "Test Video Title" in response.text
    assert "Salvar" in response.text


def test_preview_youtube_invalid_url(auth_client):
    """POST /htmx/library/preview with invalid URL returns error."""
    response = auth_client.post(
        "/htmx/library/preview",
        data={
            "type": "youtube",
            "url": "https://notayoutubeurl.com/video",
            "subject_id": "1",
        },
    )
    assert response.status_code == 200
    assert "inválida" in response.text.lower() or "erro" in response.text.lower()


def test_preview_pdf_returns_preview(auth_client, tmp_path):
    """POST /htmx/library/preview with type=pdf returns preview HTML."""
    # Create a minimal valid PDF
    pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"

    response = auth_client.post(
        "/htmx/library/preview",
        data={"type": "pdf", "subject_id": "1"},
        files={"file": ("test-document.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    assert "test-document" in response.text
    assert "Salvar" in response.text


def test_save_youtube_item(auth_client):
    """POST /htmx/library/save creates a library item."""
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
    assert "My Video" in response.text


def test_save_pdf_item(auth_client):
    """POST /htmx/library/save creates a PDF library item."""
    response = auth_client.post(
        "/htmx/library/save",
        data={
            "subject_id": "1",
            "type": "pdf",
            "name": "My Document",
            "file_path": "testuser/pdfs/fake.pdf",
            "image_path": "testuser/thumbnails/fake.jpg",
        },
    )
    assert response.status_code == 200
    assert "My Document" in response.text


def test_save_requires_auth(tmp_path):
    """POST /htmx/library/save without auth redirects."""
    from app.main import app
    client = TestClient(app)
    response = client.post(
        "/htmx/library/save",
        data={"subject_id": "1", "type": "youtube", "name": "X", "url": "http://x.com"},
        follow_redirects=False,
    )
    assert response.status_code == 303
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_library.py -v`
Expected: Tests fail because the endpoints don't exist yet. Tests in `tests/test_home.py` should still pass.

Run: `pytest tests/test_home.py -v`
Expected: PASS (confirms conftest changes don't break existing tests).

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_library.py
git commit -m "test: add library endpoint tests, update conftest schema"
```

---

### Task 4: Backend — Preview Endpoint

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add imports at top of main.py**

Add after the existing imports (line 5, after `from pathlib import Path`):

```python
import httpx
import fitz  # pymupdf
```

- [ ] **Step 2: Add the preview endpoint**

Add before the `# --- Public HTMX routes ---` comment (before line 554):

```python
MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB


@app.post("/htmx/library/preview")
async def htmx_library_preview(
    request: Request,
    type: str = Form(...),
    subject_id: int = Form(...),
    url: str | None = Form(None),
    file: UploadFile | None = File(None),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    # Verify subject belongs to user
    row = await db.execute(
        "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404)

    username = user["username"]
    thumb_dir = Path("midias") / username / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    if type == "youtube":
        if not url:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Informe a URL do vídeo."}),
            )
        m = YOUTUBE_RE.search(url)
        if not m:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "URL do YouTube inválida."}),
            )
        video_id = m.group(1)

        # Fetch title via oEmbed
        title = url
        try:
            oembed_resp = httpx.get(
                "https://noembed.com/embed",
                params={"url": f"https://www.youtube.com/watch?v={video_id}"},
                timeout=10,
            )
            oembed_resp.raise_for_status()
            title = oembed_resp.json().get("title", url)
        except Exception:
            pass

        # Download thumbnail
        thumb_filename = f"{uuid.uuid4().hex}.jpg"
        thumb_path = thumb_dir / thumb_filename
        try:
            thumb_resp = httpx.get(
                f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                timeout=10,
            )
            thumb_resp.raise_for_status()
            thumb_path.write_bytes(thumb_resp.content)
        except Exception:
            thumb_path = None

        image_path = f"{username}/thumbnails/{thumb_filename}" if thumb_path else None

        return templates.TemplateResponse(
            request=request,
            name="partials/library_preview.html",
            context=_ctx(request, {
                "preview_type": "youtube",
                "preview_name": title,
                "preview_url": url,
                "preview_image_path": image_path,
                "subject_id": subject_id,
            }),
        )

    elif type == "pdf":
        if not file or not file.filename:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Selecione um arquivo PDF."}),
            )

        contents = await file.read()
        if len(contents) > MAX_PDF_SIZE:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Arquivo muito grande (máx. 50MB)."}),
            )

        # Save PDF
        pdf_dir = Path("midias") / username / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_filename = f"{uuid.uuid4().hex}.pdf"
        pdf_path = pdf_dir / pdf_filename
        pdf_path.write_bytes(contents)

        # Generate thumbnail from first page
        thumb_filename = f"{uuid.uuid4().hex}.jpg"
        thumb_path = thumb_dir / thumb_filename
        try:
            doc = fitz.open(stream=contents, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(600 / page.rect.width, 600 / page.rect.width))
            pix.save(str(thumb_path))
            doc.close()
        except Exception:
            thumb_path = None

        image_path = f"{username}/thumbnails/{thumb_filename}" if thumb_path else None
        original_name = Path(file.filename).stem

        return templates.TemplateResponse(
            request=request,
            name="partials/library_preview.html",
            context=_ctx(request, {
                "preview_type": "pdf",
                "preview_name": original_name,
                "preview_file_path": f"{username}/pdfs/{pdf_filename}",
                "preview_image_path": image_path,
                "subject_id": subject_id,
            }),
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/library_preview.html",
        context=_ctx(request, {"error": "Tipo inválido."}),
    )
```

- [ ] **Step 3: Run preview tests**

Run: `pytest tests/test_library.py::test_preview_youtube_returns_preview tests/test_library.py::test_preview_youtube_invalid_url tests/test_library.py::test_preview_pdf_returns_preview -v`
Expected: Fails because the templates don't exist yet. That's correct — we'll create them in Task 6.

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: add library preview endpoint"
```

---

### Task 5: Backend — Save Endpoint

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add the save endpoint**

Add right after the preview endpoint:

```python
@app.post("/htmx/library/save")
async def htmx_library_save(
    request: Request,
    subject_id: int = Form(...),
    type: str = Form(...),
    name: str = Form(...),
    url: str | None = Form(None),
    file_path: str | None = Form(None),
    image_path: str | None = Form(None),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    name = name.strip()
    if not name:
        return Response(status_code=422, content="Nome é obrigatório.")

    # Verify subject belongs to user
    row = await db.execute(
        "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404)

    # Get next position
    row = await db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM library_items WHERE subject_id = ?",
        (subject_id,),
    )
    next_pos = (await row.fetchone())["next_pos"]

    cursor = await db.execute(
        """INSERT INTO library_items (subject_id, name, type, url, file_path, image_path, position)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (subject_id, name, type, url, file_path, image_path, next_pos),
    )
    await db.commit()

    # Build the item dict for the template
    item = {
        "id": cursor.lastrowid,
        "name": name,
        "type": type,
        "url": url,
        "file_path": file_path,
        "image_path": image_path,
    }
    if type == "youtube" and url:
        m = YOUTUBE_RE.search(url)
        item["thumbnail_url"] = f"https://img.youtube.com/vi/{m.group(1)}/mqdefault.jpg" if m else None
    else:
        item["thumbnail_url"] = None

    return templates.TemplateResponse(
        request=request,
        name="partials/library_item.html",
        context=_ctx(request, {"item": item}),
    )
```

- [ ] **Step 2: Update the topics route thumbnail logic**

In `app/main.py`, the `subject_topics` route (around line 526-534) checks `item["type"] == "video"`. Update to `"youtube"`:

Replace:
```python
    for item in library_items:
        if item["type"] == "video" and item["url"]:
```

With:
```python
    for item in library_items:
        if item["type"] == "youtube" and item["url"]:
```

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add library save endpoint, update type check to youtube"
```

---

### Task 6: Frontend — Template Partials

**Files:**
- Create: `app/templates/partials/library_preview.html`
- Create: `app/templates/partials/library_item.html`
- Create: `app/templates/partials/library_add_modal.html`

- [ ] **Step 1: Create library_preview.html**

This is the HTMX fragment returned by `/htmx/library/preview`.

```html
{% if error %}
<div class="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800">
  <svg class="w-5 h-5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
  </svg>
  <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
</div>
{% else %}
<form hx-post="/htmx/library/save" hx-target="#library-items-list" hx-swap="beforeend" hx-on::after-request="if(event.detail.successful) { document.dispatchEvent(new CustomEvent('close-add-modal')) }">
  <input type="hidden" name="subject_id" value="{{ subject_id }}">
  <input type="hidden" name="type" value="{{ preview_type }}">
  {% if preview_type == 'youtube' %}
  <input type="hidden" name="url" value="{{ preview_url }}">
  {% elif preview_type == 'pdf' %}
  <input type="hidden" name="file_path" value="{{ preview_file_path }}">
  {% endif %}
  <input type="hidden" name="image_path" value="{{ preview_image_path or '' }}">

  <!-- Success indicator -->
  <div class="flex items-center gap-2 p-2 rounded-lg bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 mb-3">
    <svg class="w-4 h-4 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
    </svg>
    <span class="text-xs text-teal-600 dark:text-teal-400 truncate">
      {% if preview_type == 'youtube' %}{{ preview_url }}{% else %}PDF carregado{% endif %}
    </span>
  </div>

  <!-- Thumbnail -->
  {% if preview_image_path %}
  <div class="aspect-video rounded-lg overflow-hidden bg-slate-100 dark:bg-neutral-800 mb-3">
    <img src="/midias/{{ preview_image_path }}" alt="Preview" class="w-full h-full object-cover">
  </div>
  {% endif %}

  <!-- Editable name -->
  <div class="mb-4">
    <label class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1">Nome</label>
    <input type="text" name="name" value="{{ preview_name }}"
           class="w-full rounded-lg border border-slate-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
           required>
  </div>

  <!-- Save button -->
  <button type="submit"
          class="w-full h-10 rounded-lg bg-teal-500 hover:bg-teal-600 text-white text-sm font-semibold transition-colors cursor-pointer">
    Salvar na biblioteca
  </button>
</form>
{% endif %}
```

- [ ] **Step 2: Create library_item.html**

This is a single library item card used in the drawer. Extract from `topics.html` lines 115-174:

```html
{% from "macros/buttons.html" import btn_icon %}
<div x-data="{ menu: false }" class="group">
  <div class="relative aspect-video rounded-lg overflow-hidden bg-slate-100 dark:bg-neutral-800 border border-slate-200 dark:border-neutral-700 cursor-pointer" @click="$dispatch('open-library-modal', { type: '{{ item.type }}', url: '{{ item.url or '' }}', name: '{{ item.name | e }}' })">
    <div class="w-full h-full">
      {% if item.thumbnail_url %}
      <img src="{{ item.thumbnail_url }}" alt="{{ item.name }}" class="w-full h-full object-cover">
      {% elif item.image_path %}
      <img src="/midias/{{ item.image_path }}" alt="{{ item.name }}" class="w-full h-full object-cover">
      {% else %}
      <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-teal-200 to-purple-300 dark:from-teal-900 dark:to-purple-950">
        {% if item.type == 'youtube' %}
        <svg class="w-10 h-10 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        {% else %}
        <svg class="w-10 h-10 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        {% endif %}
      </div>
      {% endif %}
    </div>
    <!-- 3-dot menu -->
    <div class="absolute top-1.5 right-1.5">
      {{ btn_icon(
        icon='<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z"/></svg>',
        click='menu = !menu',
        bg='bg-white/50 hover:bg-white/70 dark:bg-black/40 dark:hover:bg-black/60',
        text_color='text-slate-700 dark:text-white',
        extra_class='backdrop-blur-sm'
      ) }}
      <div
        x-show="menu"
        x-cloak
        @click.outside="menu = false"
        x-transition:enter="transition ease-out duration-100"
        x-transition:enter-start="opacity-0 scale-95"
        x-transition:enter-end="opacity-100 scale-100"
        x-transition:leave="transition ease-in duration-75"
        x-transition:leave-start="opacity-100 scale-100"
        x-transition:leave-end="opacity-0 scale-95"
        class="absolute right-0 mt-1 w-40 bg-white dark:bg-neutral-800 rounded-lg border border-slate-200 dark:border-neutral-700 shadow-lg overflow-hidden z-10"
      >
        <button @click="menu = false" class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
          <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          Recarregar
        </button>
        <button @click="menu = false" class="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors cursor-pointer">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
          </svg>
          Excluir
        </button>
      </div>
    </div>
  </div>
  <p @click="$dispatch('open-library-modal', { type: '{{ item.type }}', url: '{{ item.url or '' }}', name: '{{ item.name | e }}' })" class="mt-1.5 text-sm font-medium text-slate-700 dark:text-neutral-300 group-hover:text-[#26a69a] dark:group-hover:text-teal-400 transition-colors cursor-pointer">{{ item.name }}</p>
</div>
```

- [ ] **Step 3: Create library_add_modal.html**

```html
{% from "macros/buttons.html" import btn_icon %}
<div
  x-data="{
    show: false,
    selectedType: '',
    loading: false,
    selectType(t) {
      this.selectedType = t;
    },
    reset() {
      this.show = false;
      this.selectedType = '';
      this.loading = false;
      const previewArea = document.getElementById('library-preview-area');
      if (previewArea) previewArea.innerHTML = '';
    }
  }"
  @open-add-modal.window="show = true"
  @close-add-modal.window="reset()"
  @keydown.escape.window="reset()"
>
  <div x-show="show" x-cloak class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div x-show="show" @click="reset()" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100" x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0" class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>

    <!-- Panel -->
    <div x-show="show" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 scale-95" x-transition:enter-end="opacity-100 scale-100" x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100 scale-100" x-transition:leave-end="opacity-0 scale-95" class="relative bg-white dark:bg-neutral-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">

      <!-- Header -->
      <div class="flex items-center justify-between px-5 pt-5 pb-2">
        <h3 class="text-base font-bold text-slate-700 dark:text-neutral-300">Adicionar à Biblioteca</h3>
        {{ btn_icon(
          icon='<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
          click='reset()',
        ) }}
      </div>

      <div class="px-5 pb-5">
        <!-- Type selector: two cards -->
        <div class="flex gap-3 mb-4">
          <button @click="selectType('youtube')"
                  :class="selectedType === 'youtube' ? 'bg-teal-500 border-teal-500 text-white' : 'bg-slate-50 dark:bg-neutral-700 border-slate-200 dark:border-neutral-600 text-slate-500 dark:text-neutral-400'"
                  class="flex-1 flex flex-col items-center gap-1.5 py-4 rounded-xl border-2 transition-all cursor-pointer"
                  :disabled="loading">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span class="text-xs font-bold uppercase tracking-wider">YouTube</span>
          </button>
          <button @click="selectType('pdf')"
                  :class="selectedType === 'pdf' ? 'bg-teal-500 border-teal-500 text-white' : 'bg-slate-50 dark:bg-neutral-700 border-slate-200 dark:border-neutral-600 text-slate-500 dark:text-neutral-400'"
                  class="flex-1 flex flex-col items-center gap-1.5 py-4 rounded-xl border-2 transition-all cursor-pointer"
                  :disabled="loading">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <span class="text-xs font-bold uppercase tracking-wider">PDF</span>
          </button>
        </div>

        <!-- YouTube input -->
        <div x-show="selectedType === 'youtube'" x-transition>
          <form hx-post="/htmx/library/preview"
                hx-target="#library-preview-area"
                hx-swap="innerHTML"
                hx-indicator="#preview-spinner"
                @htmx:before-request="loading = true"
                @htmx:after-request="loading = false">
            <input type="hidden" name="type" value="youtube">
            <input type="hidden" name="subject_id" value="{{ subject.id }}">
            <div class="mb-3">
              <label class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1">URL do vídeo</label>
              <input type="url" name="url" placeholder="https://youtube.com/watch?v=..."
                     class="w-full rounded-lg border border-slate-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                     required>
            </div>
            <button type="submit" :disabled="loading"
                    class="w-full h-10 rounded-lg bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-white text-sm font-semibold transition-colors cursor-pointer flex items-center justify-center gap-2">
              <svg id="preview-spinner" class="htmx-indicator w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Buscar vídeo
            </button>
          </form>
        </div>

        <!-- PDF input -->
        <div x-show="selectedType === 'pdf'" x-transition>
          <form hx-post="/htmx/library/preview"
                hx-target="#library-preview-area"
                hx-swap="innerHTML"
                hx-encoding="multipart/form-data"
                hx-indicator="#pdf-spinner"
                @htmx:before-request="loading = true"
                @htmx:after-request="loading = false">
            <input type="hidden" name="type" value="pdf">
            <input type="hidden" name="subject_id" value="{{ subject.id }}">
            <div class="mb-3">
              <label class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1">Arquivo PDF</label>
              <input type="file" name="file" accept=".pdf"
                     @change="if($el.files.length) $el.closest('form').requestSubmit()"
                     class="w-full text-sm text-slate-700 dark:text-neutral-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-teal-50 file:text-teal-600 dark:file:bg-teal-900/30 dark:file:text-teal-400 file:cursor-pointer hover:file:bg-teal-100 dark:hover:file:bg-teal-900/50">
            </div>
            <div id="pdf-spinner" class="htmx-indicator flex items-center justify-center gap-2 py-2 text-sm text-slate-500 dark:text-neutral-400">
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Processando PDF...
            </div>
          </form>
        </div>

        <!-- Preview area (HTMX target) -->
        <div id="library-preview-area" class="mt-3"></div>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_library.py -v`
Expected: `test_preview_youtube_returns_preview`, `test_preview_youtube_invalid_url`, `test_preview_pdf_returns_preview`, `test_save_youtube_item`, `test_save_pdf_item`, `test_save_requires_auth` all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/templates/partials/library_preview.html app/templates/partials/library_item.html app/templates/partials/library_add_modal.html
git commit -m "feat: add library modal template partials"
```

---

### Task 7: Wire Modal into Topics Page

**Files:**
- Modify: `app/templates/topics.html`

- [ ] **Step 1: Include the add modal partial**

At the bottom of `topics.html`, just before `{% endblock %}` (line 375), add:

```html
{% include "partials/library_add_modal.html" %}
```

- [ ] **Step 2: Wire the "+" button to open the add modal**

In `topics.html` line 99, the `btn_icon` for "Adicionar conteúdo" needs a click handler. Replace lines 98-104:

```html
        {{ btn_icon(
          icon='<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>',
          bg='bg-teal-500 hover:bg-teal-600 border border-teal-600 dark:border-teal-400 shadow-lg',
          text_color='text-white',
          extra_class='flex-shrink-0',
          title='Adicionar conteúdo',
          click='$dispatch(\'open-add-modal\')'
        ) }}
```

- [ ] **Step 3: Add id to library items list for HTMX targeting**

In `topics.html`, the library items list container (line 113) needs an id for HTMX swap targeting. Replace line 113:

```html
      <div id="library-items-list" class="space-y-4">
```

- [ ] **Step 4: Replace inline library item markup with partial**

Replace the `{% for item in library_items %}` loop (lines 114-176) with:

```html
        {% for item in library_items %}
        {% include "partials/library_item.html" %}
        {% endfor %}
```

- [ ] **Step 5: Update the type check in the library item modal**

In the existing Library Item Modal at the bottom of `topics.html` (around line 285), the `open-library-modal` event handler and the fallback template check for `type === 'video'`. These need to work with both `'youtube'` and `'video'` for backwards compatibility with the template. No change needed since the dispatch in `library_item.html` already sends `item.type` which is `'youtube'` from the DB, and the modal's video embed check (`type === 'video'`) needs to also accept `'youtube'`.

Update the `open` method (around line 314):

Replace:
```javascript
    open(detail) {
      this.type = detail.type || '';
```

With:
```javascript
    open(detail) {
      this.type = detail.type === 'youtube' ? 'video' : (detail.type || '');
```

This maps `youtube` back to `video` for the existing viewer modal logic, which uses `type === 'video'` throughout.

- [ ] **Step 6: Run all tests**

Run: `pytest -v`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: wire library add modal into topics page"
```

---

### Task 8: Verify End-to-End

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Start dev server and test manually**

Run: `make dev`

Manual test checklist:
1. Navigate to a subject's topics page
2. Click "Biblioteca" to open the drawer
3. Click "+" button — modal opens with YouTube/PDF cards
4. Select YouTube, paste a real YouTube URL, click "Buscar vídeo"
5. Verify: spinner shows, then preview appears with thumbnail + title
6. Edit the name, click "Salvar" — item appears in drawer, modal closes
7. Repeat with a PDF file upload
8. Verify thumbnails are saved in `midias/{username}/thumbnails/`
9. Verify PDFs are saved in `midias/{username}/pdfs/`
10. Click on new items in drawer — viewer modal opens correctly

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: end-to-end adjustments for library add modal"
```
