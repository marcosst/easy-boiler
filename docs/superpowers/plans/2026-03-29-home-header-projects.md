# Home Page — Header + Grade de Projetos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a tela home com header (logo + menu do usuário com dropdown Alpine.js) e grade responsiva de projetos 16:9 com dados mock.

**Architecture:** Substituir o `index.html` atual pela nova `home.html`, atualizar `base.html` para usar Tailwind CDN no lugar do CSS vanilla, e atualizar a rota `GET /` em `main.py` para passar contexto `user` e `projects` mock ao template.

**Tech Stack:** FastAPI, Jinja2, Tailwind CSS (CDN), Alpine.js (CDN já presente), httpx + pytest para testes de rota.

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `app/templates/base.html` | Modificar | Trocar `<link>` CSS por CDN Tailwind |
| `app/templates/home.html` | Criar | Template da home: header + dropdown + grid |
| `app/main.py` | Modificar | Rota `/` com contexto `user` + `projects` mock |
| `tests/test_home.py` | Criar | Testes da rota e renderização |
| `pyproject.toml` | Modificar | Adicionar `httpx` e `pytest` como dev deps |

---

## Task 1: Adicionar dependências de teste

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Adicionar `httpx` e `pytest` ao pyproject.toml**

Abra `pyproject.toml` e adicione a seção de dev dependencies:

```toml
[project]
name = "easy-boiler"
version = "0.1.0"
description = "FastAPI boilerplate with a YouTube transcript helper script."
requires-python = ">=3.12"
dependencies = [
    "aiosqlite",
    "fastapi",
    "jinja2",
    "python-dotenv",
    "yt-dlp",
    "uvicorn[standard]",
    "youtube-transcript-api",
]

[tool.uv]
package = false

[dependency-groups]
dev = [
    "httpx>=0.27",
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

- [ ] **Step 2: Instalar as dependências**

```bash
uv sync --group dev
```

Esperado: instalação sem erros, `httpx` e `pytest` disponíveis.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add httpx and pytest as dev dependencies"
```

---

## Task 2: Escrever o teste da rota home (TDD)

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_home.py`

- [ ] **Step 1: Criar `tests/__init__.py` vazio**

```bash
mkdir -p tests && touch tests/__init__.py
```

- [ ] **Step 2: Criar `tests/test_home.py` com os testes**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_home_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_home_contains_projetos_title():
    response = client.get("/")
    assert "Projetos" in response.text


def test_home_contains_user_name():
    response = client.get("/")
    assert "Usuário Demo" in response.text


def test_home_contains_project_names():
    response = client.get("/")
    assert "Projeto Alpha" in response.text
    assert "Projeto Beta" in response.text
```

- [ ] **Step 3: Rodar os testes para confirmar que falham**

```bash
uv run pytest tests/test_home.py -v
```

Esperado: FAIL — os testes devem falhar pois o template/contexto ainda não foram criados.

---

## Task 3: Atualizar `base.html` para Tailwind

**Files:**
- Modify: `app/templates/base.html`

- [ ] **Step 1: Substituir o conteúdo de `base.html`**

Substituir o arquivo inteiro por:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}App{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://unpkg.com/alpinejs@3.14.3/dist/cdn.min.js"></script>
    <script src="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"></script>
</head>
<body class="bg-slate-100 min-h-screen font-sans">
    {% block content %}{% endblock %}
</body>
</html>
```

> O `static/css/style.css` não é deletado, apenas deixa de ser carregado.

- [ ] **Step 2: Commit**

```bash
git add app/templates/base.html
git commit -m "chore: replace vanilla CSS with Tailwind CDN in base.html"
```

---

## Task 4: Criar o template `home.html`

**Files:**
- Create: `app/templates/home.html`

- [ ] **Step 1: Criar `app/templates/home.html`**

```html
{% extends "base.html" %}

{% block title %}Home{% endblock %}

{% block content %}
<!-- HEADER -->
<header class="bg-white border-b border-slate-200 shadow-sm">
  <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">

    <!-- Logo -->
    <a href="/">
      <img src="/static/logo-rect.svg" alt="Logo" class="h-8 w-auto">
    </a>

    <!-- User menu -->
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
        <!-- Avatar + nome + email -->
        <div class="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
          <div class="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
            {{ user.initials }}
          </div>
          <div class="min-w-0">
            <div class="text-sm font-semibold text-slate-800 truncate">{{ user.name }}</div>
            <div class="text-xs text-slate-400 truncate">{{ user.email }}</div>
          </div>
        </div>

        <!-- Itens -->
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
</header>

<!-- CONTEÚDO -->
<main class="max-w-7xl mx-auto px-6 py-8">
  <h1 class="text-2xl font-bold text-slate-800 mb-6">Projetos</h1>

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
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
  </div>
</main>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/home.html
git commit -m "feat: add home.html template with header and projects grid"
```

---

## Task 5: Atualizar a rota `/` em `main.py`

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Substituir o conteúdo de `app/main.py`**

```python
from fastapi import FastAPI, Request
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
    {"id": 1, "name": "Projeto Alpha", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-blue-500 to-violet-500"},
    {"id": 2, "name": "Projeto Beta", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-emerald-400 to-blue-500"},
    {"id": 3, "name": "Projeto Gamma", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-amber-400 to-red-500"},
    {"id": 4, "name": "Projeto Delta", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-indigo-500 to-pink-500"},
    {"id": 5, "name": "Projeto Epsilon", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-cyan-400 to-teal-500"},
    {"id": 6, "name": "Projeto Zeta", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-rose-400 to-orange-400"},
]


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": MOCK_USER, "projects": MOCK_PROJECTS},
    )


@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html")
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: update home route with mock user and projects context"
```

---

## Task 6: Rodar os testes e verificar

**Files:**
- Test: `tests/test_home.py`

- [ ] **Step 1: Rodar todos os testes**

```bash
uv run pytest tests/test_home.py -v
```

Esperado: 4 testes PASS.

```
tests/test_home.py::test_home_returns_200 PASSED
tests/test_home.py::test_home_contains_projetos_title PASSED
tests/test_home.py::test_home_contains_user_name PASSED
tests/test_home.py::test_home_contains_project_names PASSED
```

- [ ] **Step 2: Subir o servidor e verificar visualmente**

```bash
make dev
```

Abrir `http://localhost:8000` e verificar:
- Header com logo à esquerda.
- Pill com iniciais "UD" + "Usuário Demo" à direita.
- Clicar no pill: dropdown abre com avatar, nome, email, Meu Perfil, Configurações, Sair.
- Dropdown fecha ao clicar fora ou pressionar Esc.
- Grade com 6 projetos coloridos em 3 colunas (desktop).

- [ ] **Step 3: Commit final**

```bash
git add tests/
git commit -m "test: add home route tests"
```
