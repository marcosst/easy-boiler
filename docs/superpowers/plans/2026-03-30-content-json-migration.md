# content_md to content_json Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `content_md` with `content_json` in the subjects table, render topics from structured JSON, add PDF preview to the modal, seed example data, and clean up the old markdown parser.

**Architecture:** New dbmate migration replaces the column via table recreation (SQLite pattern). The markdown parser is removed entirely. The topics template renders from the JSON structure directly. A seed script populates example data for user "marcos@medire.com.br".

**Tech Stack:** SQLite (dbmate migrations), FastAPI, Jinja2, Alpine.js, HTMX, Python sqlite3 (seed script)

---

### Task 1: Database Migration — Replace content_md with content_json

**Files:**
- Create: `db/migrations/20260330200000_content_json.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- migrate:up

CREATE TABLE subjects_new (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    shortname  TEXT    NOT NULL UNIQUE
                       CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public  INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    owner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    image_path TEXT,
    content_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO subjects_new (id, name, shortname, is_public, owner_id, image_path, content_json, created_at, updated_at)
SELECT id, name, shortname, is_public, owner_id, image_path, NULL, created_at, updated_at
FROM subjects;

DROP TABLE subjects;
ALTER TABLE subjects_new RENAME TO subjects;

CREATE INDEX idx_subjects_owner ON subjects(owner_id);

-- migrate:down

CREATE TABLE subjects_old (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    shortname  TEXT    NOT NULL UNIQUE
                       CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public  INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    owner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    image_path TEXT,
    content_md TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO subjects_old (id, name, shortname, is_public, owner_id, image_path, content_md, created_at, updated_at)
SELECT id, name, shortname, is_public, owner_id, image_path, NULL, created_at, updated_at
FROM subjects;

DROP TABLE subjects;
ALTER TABLE subjects_old RENAME TO subjects;

CREATE INDEX idx_subjects_owner ON subjects(owner_id);
```

- [ ] **Step 2: Run the migration**

Run: `make migrate`
Expected: Migration applies successfully, no errors.

- [ ] **Step 3: Verify the schema**

Run: `sqlite3 data/data.db ".schema subjects"`
Expected: Table has `content_json TEXT` instead of `content_md TEXT`. Index `idx_subjects_owner` exists.

- [ ] **Step 4: Commit**

```bash
git add db/migrations/20260330200000_content_json.sql db/schema.sql
git commit -m "feat: migrate subjects table from content_md to content_json"
```

---

### Task 2: Remove Markdown Parser and Update main.py Imports

**Files:**
- Remove: `app/md_parser.py`
- Modify: `app/main.py` (lines 3-4, 27)
- Modify: `pyproject.toml` (line 11)

- [ ] **Step 1: Delete md_parser.py**

Delete the file `app/md_parser.py`.

- [ ] **Step 2: Update imports in main.py**

Remove these lines from `app/main.py`:

```python
# Remove line 4:
import markdown as md

# Remove line 27:
from app.md_parser import get_detail_content, parse_topics_md
```

Add this import at the top of `app/main.py` (after the existing `import re`):

```python
import json
```

- [ ] **Step 3: Add parse_topics_json function to main.py**

Add this function in `app/main.py` after the `_ctx` function (after line 49):

```python
def parse_topics_json(content_json: str | None) -> list:
    """Parse JSON content into a list of topics."""
    if not content_json:
        return []
    data = json.loads(content_json)
    return data.get("topicos", [])
```

- [ ] **Step 4: Remove the markdown dependency from pyproject.toml**

In `pyproject.toml`, remove the line `"markdown",` from dependencies.

- [ ] **Step 5: Sync dependencies**

Run: `make setup`
Expected: Dependencies sync without `markdown` package.

- [ ] **Step 6: Commit**

```bash
git add app/md_parser.py app/main.py pyproject.toml uv.lock
git commit -m "refactor: remove markdown parser, add JSON topic parser"
```

---

### Task 3: Update Topics Route — Use content_json

**Files:**
- Modify: `app/main.py` (lines 495-540, 558-581)

- [ ] **Step 1: Update the subject_topics route**

In `app/main.py`, replace the `subject_topics` route (starting at line 495). Change the SQL query and parser call:

Replace this block in the route function:

```python
    row = await db.execute(
        """
        SELECT s.id, s.name, s.shortname, s.content_md, s.image_path, s.is_public
        FROM subjects s
        JOIN users u ON s.owner_id = u.id
        WHERE u.username = ? AND s.shortname = ?
        """,
        (username, shortname),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    topics = parse_topics_md(subject["content_md"])
```

With:

```python
    row = await db.execute(
        """
        SELECT s.id, s.name, s.shortname, s.content_json, s.image_path, s.is_public
        FROM subjects s
        JOIN users u ON s.owner_id = u.id
        WHERE u.username = ? AND s.shortname = ?
        """,
        (username, shortname),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    topics = parse_topics_json(subject["content_json"])
```

- [ ] **Step 2: Remove the htmx_detail route and related code**

Remove the entire `htmx_detail` route function (lines 558-581):

```python
@app.get("/htmx/details/{username}/{shortname}/{detail_id}")
async def htmx_detail(request: Request, username: str, shortname: str, detail_id: str, user=Depends(require_auth), db=Depends(get_db)):
    ...
```

Also remove the `_youtube_embed` function (lines 548-555) and the `YOUTUBE_RE` regex definition (lines 543-545) — these are no longer used since markdown content is gone.

**Keep** `YOUTUBE_RE` only if it's still used elsewhere. Check: it's used in the library items loop in `subject_topics` route (line 522-524) for generating thumbnail URLs. So **keep YOUTUBE_RE** but **remove `_youtube_embed`**.

- [ ] **Step 3: Delete detail_modal.html**

Delete the file `app/templates/partials/detail_modal.html`.

- [ ] **Step 4: Commit**

```bash
git add app/main.py app/templates/partials/detail_modal.html
git commit -m "feat: switch topics route to content_json, remove detail endpoint"
```

---

### Task 4: Update Topics Template — Render from JSON

**Files:**
- Modify: `app/templates/topics.html` (lines 220-302)

- [ ] **Step 1: Replace the topics accordion section**

In `app/templates/topics.html`, replace the topics section (lines 220-274) with the new JSON-based rendering. The structure stays the same (3-level accordion) but field names change:

Replace this block:

```html
    <div class="space-y-3">
      {% for topic in topics %}
      <!-- Level 1: Tópico -->
      <div x-data="{ open: false }" class="bg-white dark:bg-neutral-800 rounded-xl border border-slate-200 dark:border-neutral-700 overflow-hidden">
        <button @click="open = !open" class="w-full flex items-center justify-between px-5 py-4 text-left cursor-pointer hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors">
          <span class="text-base font-bold text-slate-800 dark:text-neutral-100">{{ topic.title }}</span>
          <svg class="w-5 h-5 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <div x-show="open" x-collapse>
          {% for subtopic in topic.subtopics %}
          <!-- Level 2: Subtópico -->
          <div x-data="{ open: false }" class="border-t border-slate-100 dark:border-neutral-700">
            <button @click="open = !open" class="w-full flex items-center justify-between pl-10 pr-5 py-3 text-left cursor-pointer hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors">
              <span class="text-sm font-semibold text-slate-700 dark:text-neutral-200">{{ subtopic.title }}</span>
              <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>

            <div x-show="open" x-collapse>
              {% for detail in subtopic.details %}
              <!-- Level 3: Detalhe -->
              {% if detail.has_content %}
              <button
                hx-get="/htmx/details/{{ username }}/{{ shortname }}/{{ detail.id }}"
                hx-target="#detail-modal-content"
                hx-swap="innerHTML"
                @htmx:after-request.window="if(event.detail.target.id === 'detail-modal-content') $dispatch('open-detail-modal')"
                class="w-full text-left pl-16 pr-5 py-2.5 text-sm text-[#26a69a] dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 transition-colors cursor-pointer flex items-center gap-2"
              >
                <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                {{ detail.title }}
              </button>
              {% else %}
              <div class="pl-16 pr-5 py-2.5 text-sm text-slate-500 dark:text-neutral-400 flex items-center gap-2">
                <svg class="w-4 h-4 flex-shrink-0 text-slate-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
                </svg>
                {{ detail.title }}
              </div>
              {% endif %}
              {% endfor %}
            </div>
          </div>
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </div>
```

With:

```html
    <div class="space-y-3">
      {% for topico in topics %}
      <!-- Level 1: Tópico -->
      <div x-data="{ open: false }" class="bg-white dark:bg-neutral-800 rounded-xl border border-slate-200 dark:border-neutral-700 overflow-hidden">
        <button @click="open = !open" class="w-full flex items-center justify-between px-5 py-4 text-left cursor-pointer hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors">
          <span class="text-base font-bold text-slate-800 dark:text-neutral-100">{{ topico.titulo }}</span>
          <svg class="w-5 h-5 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <div x-show="open" x-collapse>
          {% for subtopico in topico.subtopicos %}
          <!-- Level 2: Subtópico -->
          <div x-data="{ open: false }" class="border-t border-slate-100 dark:border-neutral-700">
            <button @click="open = !open" class="w-full flex items-center justify-between pl-10 pr-5 py-3 text-left cursor-pointer hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors">
              <span class="text-sm font-semibold text-slate-700 dark:text-neutral-200">{{ subtopico.titulo }}</span>
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
                class="w-full text-left pl-16 pr-5 py-2.5 text-sm text-[#26a69a] dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 transition-colors cursor-pointer"
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
    </div>
```

- [ ] **Step 2: Remove the Detail Modal Shell**

Remove the entire "Detail Modal Shell" section (lines 279-302) — it is no longer used since details are not fetched via HTMX anymore:

```html
<!-- Detail Modal Shell -->
<div
  x-data="{ show: false }"
  @open-detail-modal.window="show = true"
  ...
</div>
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: render topics from content_json, remove detail modal"
```

---

### Task 5: Update Library Modal — Support PDF and Timestamps

**Files:**
- Modify: `app/templates/topics.html` (lines 304-366)

- [ ] **Step 1: Replace the Library Item Modal**

Replace the entire Library Item Modal section (lines 304-366) with the expanded version that supports PDF preview and video timestamps:

```html
<!-- Library Item Modal -->
<div
  x-data="{
    show: false,
    type: '',
    url: '',
    name: '',
    timestamp: '',
    page: null,
    get embedUrl() {
      if (this.type !== 'video' || !this.url) return '';
      const m = this.url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]+)/);
      if (!m) return '';
      let src = 'https://www.youtube.com/embed/' + m[1] + '?autoplay=1';
      if (this.timestamp) {
        const parts = this.timestamp.split(':').map(Number);
        let seconds = 0;
        if (parts.length === 3) seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
        else if (parts.length === 2) seconds = parts[0] * 60 + parts[1];
        else seconds = parts[0];
        if (seconds > 0) src += '&start=' + seconds;
      }
      return src;
    },
    get pdfUrl() {
      if (this.type !== 'pdf' || !this.url) return '';
      let src = this.url;
      if (this.page) src += '#page=' + this.page;
      return src;
    },
    open(detail) {
      this.type = detail.type || '';
      this.url = detail.url || '';
      this.name = detail.name || '';
      this.timestamp = detail.timestamp || '';
      this.page = detail.page || null;
      this.show = true;
    },
    close() {
      this.show = false;
      this.url = '';
    }
  }"
  @open-library-modal.window="open($event.detail)"
  @keydown.escape.window="close()"
>
  <div x-show="show" x-cloak class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div x-show="show" @click="close()" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100" x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0" class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>

    <!-- Panel -->
    <div x-show="show" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 scale-95" x-transition:enter-end="opacity-100 scale-100" x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100 scale-100" x-transition:leave-end="opacity-0 scale-95" class="relative bg-white dark:bg-neutral-800 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
      <!-- Close button -->
      {{ btn_icon(
        icon='<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
        click='close()',
        extra_class='absolute top-4 right-4 z-10'
      ) }}

      <div class="p-6">
        <!-- Title -->
        <h3 class="text-lg font-bold text-slate-800 dark:text-neutral-100 mb-4 pr-12" x-text="name"></h3>

        <!-- Video embed -->
        <template x-if="type === 'video' && embedUrl">
          <div class="aspect-video rounded-xl overflow-hidden bg-black">
            <iframe :src="embedUrl" class="w-full h-full" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
          </div>
        </template>

        <!-- PDF embed -->
        <template x-if="type === 'pdf' && pdfUrl">
          <div class="rounded-xl overflow-hidden bg-slate-100 dark:bg-neutral-900" style="height: 80vh;">
            <embed :src="pdfUrl" type="application/pdf" class="w-full h-full">
          </div>
        </template>

        <!-- Fallback for items with no url -->
        <template x-if="(type === 'video' && !embedUrl) || (type !== 'video' && type !== 'pdf')">
          <div class="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-neutral-500">
            <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <p class="text-lg font-medium">Em breve</p>
          </div>
        </template>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: expand library modal with PDF preview and video timestamps"
```

---

### Task 6: Seed Script — Example Data

**Files:**
- Create: `scripts/seed.py`

- [ ] **Step 1: Create the seed script**

Create `scripts/seed.py`:

```python
"""Seed example data for user marcos@medire.com.br (username: marcosst)."""

import json
import os
import sqlite3
from pathlib import Path

from passlib.hash import bcrypt

DB_PATH = os.getenv("DATABASE_URL", "sqlite:data/data.db").replace("sqlite:", "")


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    email = "marcos@medire.com.br"
    username = "marcosst"

    # Get or create user
    row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        user_id = row["id"]
        print(f"User '{email}' already exists (id={user_id})")
    else:
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, bcrypt.hash("senha123")),
        )
        user_id = cursor.lastrowid
        print(f"Created user '{email}' (id={user_id})")

    # Delete existing data for this user (clean seed)
    db.execute("DELETE FROM subjects WHERE owner_id = ?", (user_id,))

    subjects_data = [
        {
            "name": "Cadastro de Componentes",
            "shortname": "cadastro-componentes",
            "is_public": 1,
            "library_items": [
                {"name": "Tutorial Cadastro Completo", "type": "video", "url": "https://youtube.com/watch?v=abc001"},
                {"name": "Cadastro de Agregados", "type": "video", "url": "https://youtube.com/watch?v=abc002"},
                {"name": "Tipos de Componentes", "type": "video", "url": "https://youtube.com/watch?v=abc003"},
                {"name": "Manual de Componentes", "type": "pdf", "file_path": "/midias/marcosst/manual-componentes.pdf"},
                {"name": "Guia de Classificacao", "type": "pdf", "file_path": "/midias/marcosst/guia-classificacao.pdf"},
            ],
        },
        {
            "name": "Montagem de Modulos",
            "shortname": "montagem-modulos",
            "is_public": 1,
            "library_items": [
                {"name": "Montagem Basica", "type": "video", "url": "https://youtube.com/watch?v=mont001"},
                {"name": "Montagem Avancada", "type": "video", "url": "https://youtube.com/watch?v=mont002"},
                {"name": "Encaixes e Conexoes", "type": "video", "url": "https://youtube.com/watch?v=mont003"},
                {"name": "Manual de Montagem", "type": "pdf", "file_path": "/midias/marcosst/manual-montagem.pdf"},
                {"name": "Tabela de Medidas", "type": "pdf", "file_path": "/midias/marcosst/tabela-medidas.pdf"},
                {"name": "Checklist de Montagem", "type": "pdf", "file_path": "/midias/marcosst/checklist-montagem.pdf"},
            ],
        },
        {
            "name": "Configuracao de Ferragens",
            "shortname": "configuracao-ferragens",
            "is_public": 0,
            "library_items": [
                {"name": "Ferragens Basicas", "type": "video", "url": "https://youtube.com/watch?v=ferr001"},
                {"name": "Dobradicas e Corrediceas", "type": "video", "url": "https://youtube.com/watch?v=ferr002"},
                {"name": "Catalogo de Ferragens", "type": "pdf", "file_path": "/midias/marcosst/catalogo-ferragens.pdf"},
                {"name": "Manual Tecnico Blum", "type": "pdf", "file_path": "/midias/marcosst/manual-blum.pdf"},
                {"name": "Ajustes e Regulagens", "type": "video", "url": "https://youtube.com/watch?v=ferr003"},
            ],
        },
        {
            "name": "Renderizacao 3D",
            "shortname": "renderizacao-3d",
            "is_public": 1,
            "library_items": [
                {"name": "Introducao ao Render", "type": "video", "url": "https://youtube.com/watch?v=rend001"},
                {"name": "Iluminacao e Materiais", "type": "video", "url": "https://youtube.com/watch?v=rend002"},
                {"name": "Exportacao de Imagens", "type": "video", "url": "https://youtube.com/watch?v=rend003"},
                {"name": "Guia de Renderizacao", "type": "pdf", "file_path": "/midias/marcosst/guia-renderizacao.pdf"},
                {"name": "Biblioteca de Materiais", "type": "pdf", "file_path": "/midias/marcosst/biblioteca-materiais.pdf"},
            ],
        },
        {
            "name": "Orcamento e Propostas",
            "shortname": "orcamento-propostas",
            "is_public": 0,
            "library_items": [
                {"name": "Gerando Orcamentos", "type": "video", "url": "https://youtube.com/watch?v=orc001"},
                {"name": "Personalizando Propostas", "type": "video", "url": "https://youtube.com/watch?v=orc002"},
                {"name": "Modelo de Proposta", "type": "pdf", "file_path": "/midias/marcosst/modelo-proposta.pdf"},
                {"name": "Tabela de Precos", "type": "pdf", "file_path": "/midias/marcosst/tabela-precos.pdf"},
                {"name": "Exportacao para PDF", "type": "video", "url": "https://youtube.com/watch?v=orc003"},
            ],
        },
        {
            "name": "Instalacao em Obra",
            "shortname": "instalacao-obra",
            "is_public": 1,
            "library_items": [
                {"name": "Preparacao do Ambiente", "type": "video", "url": "https://youtube.com/watch?v=inst001"},
                {"name": "Instalacao Passo a Passo", "type": "video", "url": "https://youtube.com/watch?v=inst002"},
                {"name": "Nivelamento e Prumo", "type": "video", "url": "https://youtube.com/watch?v=inst003"},
                {"name": "Manual de Instalacao", "type": "pdf", "file_path": "/midias/marcosst/manual-instalacao.pdf"},
                {"name": "Checklist de Obra", "type": "pdf", "file_path": "/midias/marcosst/checklist-obra.pdf"},
                {"name": "Ficha de Vistoria", "type": "pdf", "file_path": "/midias/marcosst/ficha-vistoria.pdf"},
            ],
        },
    ]

    for subj in subjects_data:
        cursor = db.execute(
            "INSERT INTO subjects (name, shortname, is_public, owner_id) VALUES (?, ?, ?, ?)",
            (subj["name"], subj["shortname"], subj["is_public"], user_id),
        )
        subject_id = cursor.lastrowid

        # Insert library items and collect their IDs
        lib_ids = []
        for pos, lib in enumerate(subj["library_items"]):
            c = db.execute(
                "INSERT INTO library_items (subject_id, name, type, url, file_path, position) VALUES (?, ?, ?, ?, ?, ?)",
                (subject_id, lib["name"], lib["type"], lib.get("url"), lib.get("file_path"), pos),
            )
            lib_ids.append({"id": c.lastrowid, **lib})

        # Build content_json referencing the library items
        videos = [li for li in lib_ids if li["type"] == "video"]
        pdfs = [li for li in lib_ids if li["type"] == "pdf"]

        content = {"topicos": []}

        # Topic 1: uses first 2 videos + first pdf
        t1_passos_1 = []
        if len(videos) > 0:
            t1_passos_1.append({
                "library_id": videos[0]["id"], "acao": f"Assistir: {videos[0]['name']}",
                "timestamp": "00:00:30", "pagina": None, "trecho_referencia": "",
                "file_path": None, "url": videos[0]["url"],
            })
        if len(pdfs) > 0:
            t1_passos_1.append({
                "library_id": pdfs[0]["id"], "acao": f"Consultar: {pdfs[0]['name']}",
                "timestamp": None, "pagina": 1, "trecho_referencia": "Veja a introducao do documento",
                "file_path": pdfs[0]["file_path"], "url": None,
            })

        t1_passos_2 = []
        if len(videos) > 1:
            t1_passos_2.append({
                "library_id": videos[1]["id"], "acao": f"Assistir: {videos[1]['name']}",
                "timestamp": "00:01:15", "pagina": None, "trecho_referencia": "",
                "file_path": None, "url": videos[1]["url"],
            })
        if len(pdfs) > 0:
            t1_passos_2.append({
                "library_id": pdfs[0]["id"], "acao": f"Verificar detalhes na pagina 3",
                "timestamp": None, "pagina": 3, "trecho_referencia": "Secao de detalhamento tecnico",
                "file_path": pdfs[0]["file_path"], "url": None,
            })

        content["topicos"].append({
            "titulo": f"Introducao a {subj['name']}",
            "subtopicos": [
                {"titulo": "Conceitos iniciais", "passos": t1_passos_1},
                {"titulo": "Aprofundamento", "passos": t1_passos_2},
            ],
        })

        # Topic 2: uses remaining videos + remaining pdfs
        t2_passos_1 = []
        if len(videos) > 2:
            t2_passos_1.append({
                "library_id": videos[2]["id"], "acao": f"Assistir: {videos[2]['name']}",
                "timestamp": "00:00:42", "pagina": None, "trecho_referencia": "",
                "file_path": None, "url": videos[2]["url"],
            })
        if len(pdfs) > 1:
            t2_passos_1.append({
                "library_id": pdfs[1]["id"], "acao": f"Consultar: {pdfs[1]['name']}",
                "timestamp": None, "pagina": 2, "trecho_referencia": "Tabela de referencia",
                "file_path": pdfs[1]["file_path"], "url": None,
            })

        t2_passos_2 = []
        if len(videos) > 0:
            t2_passos_2.append({
                "library_id": videos[0]["id"], "acao": f"Revisar: {videos[0]['name']} - trecho final",
                "timestamp": "00:03:20", "pagina": None, "trecho_referencia": "",
                "file_path": None, "url": videos[0]["url"],
            })
        if len(pdfs) > 1:
            t2_passos_2.append({
                "library_id": pdfs[1]["id"], "acao": f"Confirmar procedimento na pagina 5",
                "timestamp": None, "pagina": 5, "trecho_referencia": "Procedimento de verificacao final",
                "file_path": pdfs[1]["file_path"], "url": None,
            })

        content["topicos"].append({
            "titulo": f"Pratica de {subj['name']}",
            "subtopicos": [
                {"titulo": "Execucao guiada", "passos": t2_passos_1},
                {"titulo": "Revisao e validacao", "passos": t2_passos_2},
            ],
        })

        db.execute(
            "UPDATE subjects SET content_json = ? WHERE id = ?",
            (json.dumps(content, ensure_ascii=False), subject_id),
        )
        print(f"  Created subject '{subj['name']}' with {len(lib_ids)} library items")

    db.commit()
    db.close()
    print("Seed complete!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the seed script**

Run: `python scripts/seed.py`
Expected: Output shows user creation/lookup and 6 subjects created with library items.

- [ ] **Step 3: Verify in browser**

Run: `make dev`
Navigate to `http://localhost:8000/marcosst` — should see 6 subject cards.
Click any subject — should see the topics accordion with clickable steps.
Click a video step — modal should open with YouTube embed.
Click a PDF step — modal should open with PDF embed.

- [ ] **Step 4: Commit**

```bash
git add scripts/seed.py
git commit -m "feat: add seed script with example data for marcos@medire.com.br"
```

---

### Task 7: Final Cleanup Verification

**Files:** None new — verification only.

- [ ] **Step 1: Verify no stale references remain**

Run: `grep -r "content_md" app/ --include="*.py" --include="*.html"`
Expected: No results.

Run: `grep -r "md_parser" app/ --include="*.py"`
Expected: No results.

Run: `grep -r "detail_modal" app/ --include="*.py" --include="*.html"`
Expected: No results.

Run: `grep -r "detail-modal" app/ --include="*.html"`
Expected: No results.

- [ ] **Step 2: Verify the app starts without errors**

Run: `make dev`
Expected: uvicorn starts without import errors or warnings.

- [ ] **Step 3: Spot-check the flow**

1. Go to `http://localhost:8000/marcosst`
2. Click a subject
3. Expand a topic → subtopic → click a video step (verify timestamp in URL)
4. Click a PDF step (verify PDF embed opens)
5. Open the library sidebar — click a library item (verify modal opens)

- [ ] **Step 4: Final commit if any fixups needed**

If any cleanup was needed during verification, commit it:

```bash
git add -A
git commit -m "chore: final cleanup for content_json migration"
```
