# Topics Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Topics screen with a 3-level accordion and detail modal, plus refactor the header into a reusable partial.

**Architecture:** Extract the header from `grid_page.html` into `partials/header.html` using a `header_title` context variable. Create `topics.html` extending `base.html` with the shared header and a 3-level Alpine.js accordion. Level 3 items with content load a modal via HTMX from a new `/htmx/details/{id}` route.

**Tech Stack:** FastAPI, Jinja2, Alpine.js, HTMX, Tailwind CSS, Python `markdown` library

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `app/templates/partials/header.html` | Reusable header partial |
| Modify | `app/templates/grid_page.html` | Replace inline header with include |
| Modify | `app/templates/home.html` | Set `header_title` before include |
| Modify | `app/templates/collections.html` | Set `header_title`, make cards linkable |
| Create | `app/templates/topics.html` | 3-level accordion page |
| Create | `app/templates/partials/detail_modal.html` | Modal content partial (HTMX) |
| Modify | `app/main.py` | Add mock data, topics route, HTMX detail route |
| Modify | `pyproject.toml` | Add `markdown` dependency |
| Create | `tests/test_topics.py` | Tests for topics screen and modal |

---

### Task 1: Extract Header Into Partial

**Files:**
- Create: `app/templates/partials/header.html`
- Modify: `app/templates/grid_page.html:10-141`
- Modify: `app/templates/home.html`
- Modify: `app/templates/collections.html`

- [ ] **Step 1: Create `partials/header.html`**

Extract the full `<header>...</header>` block from `grid_page.html`, replacing `{% block page_title %}{% endblock %}` with `{{ header_title | safe }}`:

```html
<!-- HEADER -->
<header class="bg-white dark:bg-neutral-950 border-b border-slate-200 dark:border-neutral-800 shadow-sm transition-colors">
  <div class="max-w-7xl mx-auto px-6 h-16 grid grid-cols-3 items-center">

    <!-- Logo (left) -->
    <a href="/">
      <img src="/static/resumiu-header.svg" alt="Logo" class="h-14 w-auto">
    </a>

    <!-- Page title (center) -->
    <div class="flex justify-center">
      {{ header_title | safe }}
    </div>

    <!-- User menu (right) -->
    <div class="flex justify-end">
      <div class="relative" x-data="{ open: false, themeOpen: false }">
        <button
          @click="open = !open"
          @keydown.escape="open = false"
          class="flex items-center gap-2 bg-slate-100 dark:bg-neutral-700 hover:bg-slate-200 dark:hover:bg-neutral-600 rounded-full py-1.5 pl-1.5 pr-3 transition-colors cursor-pointer"
          aria-haspopup="true"
          :aria-expanded="open"
        >
          <div class="w-8 h-8 rounded-full bg-brand dark:bg-brand-dark flex items-center justify-center text-white text-xs font-bold select-none">
            {{ user.initials }}
          </div>
          <span class="text-sm font-medium text-slate-700 dark:text-neutral-300">{{ user.name }}</span>
          <svg class="w-3.5 h-3.5 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <!-- Dropdown -->
        <div
          x-show="open"
          @click.outside="open = false"
          x-transition:enter="transition ease-out duration-100"
          x-transition:enter-start="opacity-0 scale-95"
          x-transition:enter-end="opacity-100 scale-100"
          x-transition:leave="transition ease-in duration-75"
          x-transition:leave-start="opacity-100 scale-100"
          x-transition:leave-end="opacity-0 scale-95"
          class="absolute right-0 mt-2 w-52 bg-white dark:bg-neutral-800 rounded-xl border border-slate-200 dark:border-neutral-700 shadow-lg overflow-hidden z-50"
          role="menu"
        >
          <div class="flex items-center gap-3 px-4 py-3 border-b border-slate-100 dark:border-neutral-700">
            <div class="w-9 h-9 rounded-full bg-brand dark:bg-brand-dark flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
              {{ user.initials }}
            </div>
            <div class="min-w-0">
              <div class="text-sm font-semibold text-slate-800 dark:text-neutral-100 truncate">{{ user.name }}</div>
              <div class="text-xs text-slate-400 dark:text-neutral-500 truncate">{{ user.email }}</div>
            </div>
          </div>
          <div class="py-1">
            <a href="/profile" class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors" role="menuitem" @click="open = false">
              <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
              </svg>
              Meu Perfil
            </a>
            <a href="/settings" class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors" role="menuitem" @click="open = false">
              <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              Configurações
            </a>
            <div class="border-t border-slate-100 dark:border-neutral-700 my-1"></div>

            <!-- Theme toggle -->
            <button @click="themeOpen = !themeOpen" class="flex items-center justify-between w-full px-4 py-2.5 text-sm text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors" role="menuitem">
              <span class="flex items-center gap-2.5">
                <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 7.66l-.71-.71M4.05 4.05l-.71-.71M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                </svg>
                Tema
              </span>
              <svg class="w-3.5 h-3.5 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="themeOpen && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            <div x-show="themeOpen" x-transition class="px-4 pb-2.5">
              <div class="flex rounded-lg bg-slate-100 dark:bg-neutral-700 p-0.5">
                <button
                  @click="setTheme('light'); open = false; themeOpen = false"
                  :class="theme === 'light' ? 'bg-white dark:bg-neutral-600 shadow-sm text-slate-800 dark:text-neutral-100' : 'text-slate-500 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-neutral-300'"
                  class="flex-1 flex items-center justify-center gap-1 rounded-md py-1.5 text-xs font-medium transition-all cursor-pointer"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 7.66l-.71-.71M4.05 4.05l-.71-.71M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                  </svg>
                  Claro
                </button>
                <button
                  @click="setTheme('dark'); open = false; themeOpen = false"
                  :class="theme === 'dark' ? 'bg-white dark:bg-neutral-600 shadow-sm text-slate-800 dark:text-neutral-100' : 'text-slate-500 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-neutral-300'"
                  class="flex-1 flex items-center justify-center gap-1 rounded-md py-1.5 text-xs font-medium transition-all cursor-pointer"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                  </svg>
                  Escuro
                </button>
                <button
                  @click="setTheme('auto'); open = false; themeOpen = false"
                  :class="theme === 'auto' ? 'bg-white dark:bg-neutral-600 shadow-sm text-slate-800 dark:text-neutral-100' : 'text-slate-500 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-neutral-300'"
                  class="flex-1 flex items-center justify-center gap-1 rounded-md py-1.5 text-xs font-medium transition-all cursor-pointer"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                  </svg>
                  Auto
                </button>
              </div>
            </div>

            <div class="border-t border-slate-100 dark:border-neutral-700 my-1"></div>
            <a href="/logout" class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors" role="menuitem">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
              Sair
            </a>
          </div>
        </div>
      </div>
    </div>

  </div>
</header>
```

- [ ] **Step 2: Update `grid_page.html` to use the partial**

Replace the entire file with:

```html
{#
  Required context variables:
    user.name      – display name shown in the avatar button
    user.initials  – shown in the avatar circle
    user.email     – shown in the dropdown identity card
    header_title   – HTML string for the center of the header (optional)
#}
{% extends "base.html" %}

{% block content %}
{% include "partials/header.html" %}

<!-- CONTENT -->
<main class="max-w-7xl mx-auto px-6 py-8">
  {% block section_title %}{% endblock %}
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
    {% block grid_items %}{% endblock %}
  </div>
</main>
{% endblock %}
```

- [ ] **Step 3: Update `home.html` to set `header_title`**

No change needed — `home.html` doesn't set `page_title` today, and the partial renders empty when `header_title` is not set (Jinja2 renders undefined as empty string).

- [ ] **Step 4: Update `collections.html` to set `header_title`**

Replace the full file with:

```html
{% extends "grid_page.html" %}

{% block title %}{{ project.name }}{% endblock %}

{% set header_title = '<span class="text-sm font-semibold text-slate-800 dark:text-neutral-100">' ~ project.name ~ '</span>' %}

{% block section_title %}
<h1 class="text-2xl font-bold text-slate-800 dark:text-neutral-100 mb-6">Coleções</h1>
{% endblock %}

{% block grid_items %}
{% for collection in collections %}
<a href="/projects/{{ project.id }}/collections/{{ collection.id }}" class="bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-sm border border-slate-200 dark:border-neutral-700 hover:shadow-md transition-shadow cursor-pointer block">
  <div class="aspect-video bg-slate-200 dark:bg-neutral-700 overflow-hidden">
    {% if collection.thumbnail_url %}
    <img src="{{ collection.thumbnail_url }}" alt="{{ collection.name }}" class="w-full h-full object-cover">
    {% else %}
    <div class="w-full h-full {{ collection.placeholder_color }}"></div>
    {% endif %}
  </div>
  <div class="p-3">
    <span class="text-sm font-medium text-slate-800 dark:text-neutral-100">{{ collection.name }}</span>
  </div>
</a>
{% endfor %}
{% endblock %}
```

Note: collection cards changed from `<div>` to `<a>` linking to `/projects/{pid}/collections/{cid}`.

- [ ] **Step 5: Run existing tests to verify no regression**

Run: `cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/ -v`
Expected: All 9 tests PASS (the header partial is identical markup, just moved)

- [ ] **Step 6: Commit**

```bash
git add app/templates/partials/header.html app/templates/grid_page.html app/templates/home.html app/templates/collections.html
git commit -m "refactor: extract header into reusable partial"
```

---

### Task 2: Add Mock Data and Routes

**Files:**
- Modify: `app/main.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `markdown` dependency**

In `pyproject.toml`, add `"markdown"` to the `dependencies` list:

```toml
dependencies = [
    "aiosqlite",
    "fastapi",
    "jinja2",
    "markdown",
    "python-dotenv",
    "yt-dlp",
    "uvicorn[standard]",
    "youtube-transcript-api",
]
```

Then run: `cd /home/ubuntu/aaaa/easy-boiler && uv sync`

- [ ] **Step 2: Add MOCK_TOPICS and MOCK_DETAILS to `main.py`**

Add after `MOCK_COLLECTIONS` dict:

```python
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
                        has_content = (d_idx % 2 == 0)  # alternating
                        detail_list.append({
                            "id": detail_id_counter,
                            "name": d_name,
                            "has_content": has_content,
                        })
                        if has_content:
                            # Alternate between video+text, video-only, text-only
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
```

- [ ] **Step 3: Add topics page route**

Add after the `collections` route:

```python
@app.get("/projects/{project_id}/collections/{collection_id}")
async def topics(request: Request, project_id: int, collection_id: int):
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
            "user": MOCK_USER,
            "project": project,
            "collection": collection,
            "topics": MOCK_TOPICS.get(collection_id, []),
        },
    )
```

- [ ] **Step 4: Add HTMX detail route**

Add after the topics route:

```python
import markdown as md

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
```

Note: the `import markdown as md` goes at the top of the file with the other imports.

- [ ] **Step 5: Commit**

```bash
git add app/main.py pyproject.toml
git commit -m "feat: add mock data and routes for topics screen and detail modal"
```

---

### Task 3: Write Tests

**Files:**
- Create: `tests/test_topics.py`

- [ ] **Step 1: Write tests**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_topics_page_returns_200():
    response = client.get("/projects/1/collections/11")
    assert response.status_code == 200


def test_topics_page_shows_project_and_collection_in_header():
    response = client.get("/projects/1/collections/11")
    assert "Projeto Alpha" in response.text
    assert "Coleção 2" in response.text


def test_topics_page_has_breadcrumb_link_to_project():
    response = client.get("/projects/1/collections/11")
    assert 'href="/projects/1"' in response.text


def test_topics_page_shows_accordion_structure():
    response = client.get("/projects/1/collections/11")
    assert "Introdução" in response.text
    assert "Conceitos Fundamentais" in response.text
    assert "Aplicações Práticas" in response.text


def test_topics_page_has_alpine_accordion():
    response = client.get("/projects/1/collections/11")
    assert "x-data" in response.text
    assert "x-show" in response.text


def test_topics_page_has_dark_mode_classes():
    response = client.get("/projects/1/collections/11")
    assert "dark:bg-neutral-900" in response.text
    assert "dark:bg-neutral-800" in response.text


def test_topics_detail_with_content_is_clickable():
    response = client.get("/projects/1/collections/11")
    assert "hx-get" in response.text
    assert "/htmx/details/" in response.text


def test_topics_invalid_project_returns_404():
    response = client.get("/projects/999/collections/11")
    assert response.status_code == 404


def test_topics_invalid_collection_returns_404():
    response = client.get("/projects/1/collections/999")
    assert response.status_code == 404


def test_htmx_detail_returns_200():
    # Get a valid detail_id from mock data
    from app.main import MOCK_DETAILS
    detail_id = next(iter(MOCK_DETAILS))
    response = client.get(f"/htmx/details/{detail_id}")
    assert response.status_code == 200


def test_htmx_detail_invalid_returns_404():
    response = client.get("/htmx/details/999999")
    assert response.status_code == 404


def test_htmx_detail_renders_youtube_iframe():
    from app.main import MOCK_DETAILS
    # Find a detail with youtube_url
    detail_id = next(
        did for did, d in MOCK_DETAILS.items() if d.get("youtube_url")
    )
    response = client.get(f"/htmx/details/{detail_id}")
    assert "youtube.com/embed" in response.text


def test_htmx_detail_renders_markdown_html():
    from app.main import MOCK_DETAILS
    # Find a detail with content_md
    detail_id = next(
        did for did, d in MOCK_DETAILS.items() if d.get("content_md")
    )
    response = client.get(f"/htmx/details/{detail_id}")
    assert "<h2>" in response.text or "<strong>" in response.text


def test_collections_cards_link_to_topics():
    response = client.get("/projects/1")
    assert "/projects/1/collections/" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/test_topics.py -v`
Expected: Most tests FAIL because templates don't exist yet

- [ ] **Step 3: Commit**

```bash
git add tests/test_topics.py
git commit -m "test: add failing tests for topics screen and detail modal"
```

---

### Task 4: Create Topics Page Template

**Files:**
- Create: `app/templates/topics.html`

- [ ] **Step 1: Create `topics.html`**

```html
{% extends "base.html" %}

{% block title %}{{ collection.name }}{% endblock %}

{% set header_title = '<a href="/projects/' ~ project.id ~ '" class="text-sm font-semibold text-slate-800 dark:text-neutral-100 hover:text-brand dark:hover:text-brand-dark transition-colors">' ~ project.name ~ '</a><span class="text-sm text-slate-400 dark:text-neutral-500 mx-1">/</span><span class="text-sm font-semibold text-slate-800 dark:text-neutral-100">' ~ collection.name ~ '</span>' %}

{% block content %}
{% include "partials/header.html" %}

<!-- CONTENT -->
<main class="max-w-7xl mx-auto px-6 py-8">
  <h1 class="text-2xl font-bold text-slate-800 dark:text-neutral-100 mb-6">Tópicos</h1>

  <div class="space-y-3">
    {% for topic in topics %}
    <!-- Level 1: Tópico -->
    <div x-data="{ open: false }" class="bg-white dark:bg-neutral-800 rounded-xl border border-slate-200 dark:border-neutral-700 overflow-hidden">
      <button @click="open = !open" class="w-full flex items-center justify-between px-5 py-4 text-left cursor-pointer hover:bg-slate-50 dark:hover:bg-neutral-750 transition-colors">
        <span class="text-base font-bold text-slate-800 dark:text-neutral-100">{{ topic.name }}</span>
        <svg class="w-5 h-5 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>

      <div x-show="open" x-collapse>
        {% for subtopic in topic.subtopics %}
        <!-- Level 2: Subtópico -->
        <div x-data="{ open: false }" class="border-t border-slate-100 dark:border-neutral-700">
          <button @click="open = !open" class="w-full flex items-center justify-between pl-10 pr-5 py-3 text-left cursor-pointer hover:bg-slate-50 dark:hover:bg-neutral-750 transition-colors">
            <span class="text-sm font-semibold text-slate-700 dark:text-neutral-200">{{ subtopic.name }}</span>
            <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

          <div x-show="open" x-collapse>
            {% for detail in subtopic.details %}
            <!-- Level 3: Detalhe -->
            {% if detail.has_content %}
            <button
              hx-get="/htmx/details/{{ detail.id }}"
              hx-target="#detail-modal-content"
              hx-swap="innerHTML"
              @htmx:after-request.window="if(event.detail.target.id === 'detail-modal-content') $dispatch('open-detail-modal')"
              class="w-full text-left pl-16 pr-5 py-2.5 text-sm text-[#26a69a] dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 transition-colors cursor-pointer flex items-center gap-2"
            >
              <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
              {{ detail.name }}
            </button>
            {% else %}
            <div class="pl-16 pr-5 py-2.5 text-sm text-slate-500 dark:text-neutral-400 flex items-center gap-2">
              <svg class="w-4 h-4 flex-shrink-0 text-slate-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
              </svg>
              {{ detail.name }}
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
</main>

<!-- Detail Modal Shell -->
<div
  x-data="{ show: false }"
  @open-detail-modal.window="show = true"
  @keydown.escape.window="show = false"
>
  <div x-show="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div x-show="show" @click="show = false" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100" x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0" class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>

    <!-- Panel -->
    <div x-show="show" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 scale-95" x-transition:enter-end="opacity-100 scale-100" x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100 scale-100" x-transition:leave-end="opacity-0 scale-95" class="relative bg-white dark:bg-neutral-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto">
      <!-- Close button -->
      <button @click="show = false" class="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-slate-100 dark:bg-neutral-700 hover:bg-slate-200 dark:hover:bg-neutral-600 transition-colors cursor-pointer">
        <svg class="w-4 h-4 text-slate-500 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>

      <!-- Dynamic content loaded by HTMX -->
      <div id="detail-modal-content"></div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Run tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/test_topics.py -v`
Expected: Most tests pass except detail modal template tests (partial not yet created)

- [ ] **Step 3: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: add topics page with 3-level accordion"
```

---

### Task 5: Create Detail Modal Partial

**Files:**
- Create: `app/templates/partials/detail_modal.html`

- [ ] **Step 1: Create `partials/detail_modal.html`**

```html
<div class="p-6">
  {% if detail.youtube_url %}
  <div class="aspect-video rounded-xl overflow-hidden mb-4 bg-black">
    <iframe
      src="{{ detail.youtube_url }}"
      class="w-full h-full"
      frameborder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen
    ></iframe>
  </div>
  {% endif %}

  {% if detail.content_html %}
  <div class="prose prose-sm dark:prose-invert max-w-none text-slate-700 dark:text-neutral-300">
    {{ detail.content_html | safe }}
  </div>
  {% endif %}
</div>
```

- [ ] **Step 2: Run all tests**

Run: `cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/detail_modal.html
git commit -m "feat: add detail modal partial with YouTube and markdown support"
```

---

### Task 6: Add Collapse Plugin and Final Polish

**Files:**
- Modify: `app/templates/base.html`

- [ ] **Step 1: Add Alpine.js collapse plugin**

The accordion uses `x-collapse` for smooth animations. Add the collapse plugin **before** the main Alpine.js script in `base.html`:

```html
<script defer src="https://unpkg.com/@alpinejs/collapse@3.14.3/dist/cdn.min.js"></script>
<script defer src="https://unpkg.com/alpinejs@3.14.3/dist/cdn.min.js"></script>
```

Replace the existing Alpine.js script tag (line 28) and add the collapse plugin before it.

- [ ] **Step 2: Run full test suite**

Run: `cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Manual verification**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`

1. Open `http://localhost:8000/` — home screen unchanged
2. Click a project → collections screen, cards now link to topics
3. Click a collection → topics screen with "Projeto / Coleção" in header
4. Expand accordion at all 3 levels
5. Click a detail with content → modal opens with video and/or text
6. Close modal via X, backdrop, Escape
7. Click project name in header → goes back to collections
8. Click logo → goes back to home
9. Toggle dark mode — all new elements styled correctly

- [ ] **Step 4: Commit**

```bash
git add app/templates/base.html
git commit -m "feat: add Alpine collapse plugin for accordion animations"
```
