# Collections Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Collections screen reachable by clicking a project card, with a shared `grid_page.html` base template used by both Home and Collections.

**Architecture:** Extract `grid_page.html` from the current `home.html` header/grid markup; refactor `home.html` to extend it; create `collections.html` and the `/projects/{id}` route with mock data.

**Tech Stack:** FastAPI, Jinja2 templates, Tailwind CSS, Alpine.js, pytest + FastAPI TestClient

---

### Task 1: Create `grid_page.html` and refactor `home.html`

**Files:**
- Create: `app/templates/grid_page.html`
- Modify: `app/templates/home.html`

- [ ] **Step 1: Verify existing tests pass before touching anything**

```bash
pytest tests/test_home.py -v
```
Expected: 4 tests PASS.

- [ ] **Step 2: Create `app/templates/grid_page.html`**

This template extracts the header and grid container from `home.html`. The header uses a 3-column CSS grid so the center column can hold a page-specific title. The `page_title` block is empty by default (home has no centered text). Child templates fill `section_title` (the `<h1>` above the grid) and `grid_items` (the cards).

```html
{% extends "base.html" %}

{% block content %}
<!-- HEADER -->
<header class="bg-white border-b border-slate-200 shadow-sm">
  <div class="max-w-7xl mx-auto px-6 h-16 grid grid-cols-3 items-center">

    <!-- Logo (left) -->
    <a href="/">
      <img src="/static/logo-rect.svg" alt="Logo" class="h-14 w-auto">
    </a>

    <!-- Page title (center) -->
    <div class="flex justify-center">
      {% block page_title %}{% endblock %}
    </div>

    <!-- User menu (right) -->
    <div class="flex justify-end">
      <div class="relative" x-data="{ open: false }">
        <button
          @click="open = !open"
          @keydown.escape="open = false"
          class="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 rounded-full py-1.5 pl-1.5 pr-3 transition-colors cursor-pointer"
          aria-haspopup="true"
          :aria-expanded="open"
        >
          <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold select-none">
            {{ user.initials }}
          </div>
          <span class="text-sm font-medium text-slate-700">{{ user.name }}</span>
          <svg class="w-3.5 h-3.5 text-slate-400 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          class="absolute right-0 mt-2 w-52 bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden z-50"
          role="menu"
        >
          <div class="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
            <div class="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
              {{ user.initials }}
            </div>
            <div class="min-w-0">
              <div class="text-sm font-semibold text-slate-800 truncate">{{ user.name }}</div>
              <div class="text-xs text-slate-400 truncate">{{ user.email }}</div>
            </div>
          </div>
          <div class="py-1">
            <a href="/profile" class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors" role="menuitem" @click="open = false">
              <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
              </svg>
              Meu Perfil
            </a>
            <a href="/settings" class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors" role="menuitem" @click="open = false">
              <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              Configurações
            </a>
            <div class="border-t border-slate-100 my-1"></div>
            <a href="/logout" class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors" role="menuitem">
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

<!-- CONTENT -->
<main class="max-w-7xl mx-auto px-6 py-8">
  {% block section_title %}{% endblock %}
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
    {% block grid_items %}{% endblock %}
  </div>
</main>
{% endblock %}
```

- [ ] **Step 3: Replace `app/templates/home.html` with a lean version that extends `grid_page.html`**

```html
{% extends "grid_page.html" %}

{% block title %}Home{% endblock %}

{% block section_title %}
<h1 class="text-2xl font-bold text-slate-800 mb-6">Projetos</h1>
{% endblock %}

{% block grid_items %}
{% for project in projects %}
<a href="/projects/{{ project.id }}" class="bg-white rounded-xl overflow-hidden shadow-sm border border-slate-200 hover:shadow-md transition-shadow cursor-pointer block">
  <div class="aspect-video bg-slate-200 overflow-hidden">
    {% if project.thumbnail_url %}
    <img src="{{ project.thumbnail_url }}" alt="{{ project.name }}" class="w-full h-full object-cover">
    {% else %}
    <div class="w-full h-full {{ project.placeholder_color }}"></div>
    {% endif %}
  </div>
  <div class="p-3">
    <span class="text-sm font-medium text-slate-800">{{ project.name }}</span>
  </div>
</a>
{% endfor %}
{% endblock %}
```

- [ ] **Step 4: Run tests to confirm no regression**

```bash
pytest tests/test_home.py -v
```
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/templates/grid_page.html app/templates/home.html
git commit -m "refactor: extract grid_page.html shared base template"
```

---

### Task 2: TDD — Collections route and template

**Files:**
- Create: `tests/test_collections.py`
- Modify: `app/main.py`
- Create: `app/templates/collections.html`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_collections.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_collections_returns_200():
    response = client.get("/projects/1")
    assert response.status_code == 200


def test_collections_returns_404_for_unknown_project():
    response = client.get("/projects/999")
    assert response.status_code == 404


def test_collections_contains_project_name():
    response = client.get("/projects/1")
    assert "Projeto Alpha" in response.text


def test_collections_contains_collection_names():
    response = client.get("/projects/1")
    assert "Coleção 1" in response.text
    assert "Coleção 2" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_collections.py -v
```
Expected: 4 tests FAIL — route `/projects/{id}` does not exist yet.

- [ ] **Step 3: Add `MOCK_COLLECTIONS` and the route to `app/main.py`**

Add `HTTPException` to the existing FastAPI import and append the data + route at the end of `app/main.py`:

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

MOCK_USER = {
    "name": "Usuário Demo",
    "email": "usuario@demo.com",
    "initials": "UD",
}

MOCK_PROJECTS = [
    {"id": 1, "name": "Projeto Alpha",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-blue-500 to-violet-500"},
    {"id": 2, "name": "Projeto Beta",    "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-emerald-400 to-blue-500"},
    {"id": 3, "name": "Projeto Gamma",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-amber-400 to-red-500"},
    {"id": 4, "name": "Projeto Delta",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-indigo-500 to-pink-500"},
    {"id": 5, "name": "Projeto Epsilon", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-cyan-400 to-teal-500"},
    {"id": 6, "name": "Projeto Zeta",    "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-rose-400 to-orange-400"},
]

_COLLECTION_COLORS = [
    "bg-gradient-to-br from-sky-400 to-blue-500",
    "bg-gradient-to-br from-violet-400 to-purple-500",
    "bg-gradient-to-br from-emerald-400 to-green-600",
    "bg-gradient-to-br from-amber-400 to-yellow-500",
    "bg-gradient-to-br from-rose-400 to-pink-500",
    "bg-gradient-to-br from-teal-400 to-cyan-500",
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


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": MOCK_USER, "projects": MOCK_PROJECTS},
    )


@app.get("/projects/{project_id}")
async def collections(request: Request, project_id: int):
    project = next((p for p in MOCK_PROJECTS if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="collections.html",
        context={
            "user": MOCK_USER,
            "project": project,
            "collections": MOCK_COLLECTIONS[project_id],
        },
    )


@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html")
```

- [ ] **Step 4: Create `app/templates/collections.html`**

```html
{% extends "grid_page.html" %}

{% block title %}{{ project.name }}{% endblock %}

{% block page_title %}
<span class="text-sm font-semibold text-slate-800">{{ project.name }}</span>
{% endblock %}

{% block section_title %}
<h1 class="text-2xl font-bold text-slate-800 mb-6">Coleções</h1>
{% endblock %}

{% block grid_items %}
{% for collection in collections %}
<div class="bg-white rounded-xl overflow-hidden shadow-sm border border-slate-200 hover:shadow-md transition-shadow cursor-pointer block">
  <div class="aspect-video bg-slate-200 overflow-hidden">
    {% if collection.thumbnail_url %}
    <img src="{{ collection.thumbnail_url }}" alt="{{ collection.name }}" class="w-full h-full object-cover">
    {% else %}
    <div class="w-full h-full {{ collection.placeholder_color }}"></div>
    {% endif %}
  </div>
  <div class="p-3">
    <span class="text-sm font-medium text-slate-800">{{ collection.name }}</span>
  </div>
</div>
{% endfor %}
{% endblock %}
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/ -v
```
Expected: all 8 tests PASS (4 home + 4 collections).

- [ ] **Step 6: Commit**

```bash
git add tests/test_collections.py app/main.py app/templates/collections.html
git commit -m "feat: add collections screen with shared grid_page base template"
```

---

## Verification

```bash
make dev
```

1. Open `http://localhost:8000/` — home screen unchanged (logo, avatar, 6 project cards)
2. Click any project card — navigates to `/projects/{id}`
3. Collections screen shows: logo left, project name centered in header, avatar right, 6 collection cards in grid with names below each card
4. Click the logo — returns to home
5. `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/projects/999` → `404`
