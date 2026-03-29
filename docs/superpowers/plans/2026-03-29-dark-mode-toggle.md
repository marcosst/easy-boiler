# Dark Mode Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dark/light/auto theme toggle to the user dropdown, with Tailwind `darkMode: 'class'` and Alpine.js managing the state via `localStorage`.

**Architecture:** Alpine.js component on `<html>` manages the `dark` class based on `localStorage` preference (default: auto/OS). A collapsible "Tema" sub-item in the user dropdown exposes 3 pill buttons (Claro/Escuro/Automático). All existing templates get `dark:` Tailwind variants.

**Tech Stack:** Tailwind CSS (CDN, `darkMode: 'class'`), Alpine.js, localStorage

---

### Task 1: Tailwind config + Alpine theme manager in `base.html`

**Files:**
- Modify: `app/templates/base.html`
- Test: `tests/test_dark_mode.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dark_mode.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_home_contains_tailwind_dark_mode_config():
    response = client.get("/")
    assert "darkMode" in response.text


def test_home_contains_theme_manager():
    response = client.get("/")
    assert "x-data" in response.text
    assert "setTheme" in response.text


def test_home_has_dark_body_class():
    response = client.get("/")
    assert "dark:bg-slate-900" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dark_mode.py -v`
Expected: 3 FAIL — no darkMode config, no theme manager, no dark classes yet.

- [ ] **Step 3: Update `app/templates/base.html`**

Replace the entire file with:

```html
<!DOCTYPE html>
<html lang="pt-BR" x-data="themeManager()" :class="{ 'dark': isDark }">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}App{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
      tailwind.config = { darkMode: 'class' }
    </script>
    <script defer src="https://unpkg.com/alpinejs@3.14.3/dist/cdn.min.js"></script>
    <script src="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"></script>
    <script>
      function themeManager() {
        return {
          theme: localStorage.getItem('theme') || 'auto',
          isDark: false,
          mediaQuery: window.matchMedia('(prefers-color-scheme: dark)'),
          init() {
            this.applyTheme();
            this.mediaQuery.addEventListener('change', () => {
              if (this.theme === 'auto') this.applyTheme();
            });
          },
          setTheme(mode) {
            this.theme = mode;
            localStorage.setItem('theme', mode);
            this.applyTheme();
          },
          applyTheme() {
            if (this.theme === 'dark') {
              this.isDark = true;
            } else if (this.theme === 'light') {
              this.isDark = false;
            } else {
              this.isDark = this.mediaQuery.matches;
            }
          }
        }
      }
    </script>
</head>
<body class="bg-slate-100 dark:bg-slate-900 min-h-screen font-sans transition-colors">
    {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dark_mode.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Run all existing tests to confirm no regression**

Run: `pytest tests/ -v`
Expected: 11 PASS (8 existing + 3 new).

- [ ] **Step 6: Commit**

```bash
git add app/templates/base.html tests/test_dark_mode.py
git commit -m "feat: add Tailwind dark mode config and Alpine theme manager"
```

---

### Task 2: "Tema" sub-item in dropdown + dark classes on `grid_page.html`

**Files:**
- Modify: `app/templates/grid_page.html`
- Modify: `tests/test_dark_mode.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_dark_mode.py`:

```python
def test_dropdown_contains_tema_toggle():
    response = client.get("/")
    assert "Tema" in response.text


def test_dropdown_contains_theme_options():
    response = client.get("/")
    assert "Claro" in response.text
    assert "Escuro" in response.text
    assert "Auto" in response.text
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `pytest tests/test_dark_mode.py::test_dropdown_contains_tema_toggle tests/test_dark_mode.py::test_dropdown_contains_theme_options -v`
Expected: 2 FAIL — no "Tema" or theme options in dropdown yet.

- [ ] **Step 3: Update `app/templates/grid_page.html`**

Replace the entire file with:

```html
{#
  Required context variables:
    user.name      – display name shown in the avatar button
    user.initials  – shown in the avatar circle
    user.email     – shown in the dropdown identity card
#}
{% extends "base.html" %}

{% block content %}
<!-- HEADER -->
<header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 shadow-sm transition-colors">
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
      <div class="relative" x-data="{ open: false, themeOpen: false }">
        <button
          @click="open = !open"
          @keydown.escape="open = false"
          class="flex items-center gap-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-full py-1.5 pl-1.5 pr-3 transition-colors cursor-pointer"
          aria-haspopup="true"
          :aria-expanded="open"
        >
          <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold select-none">
            {{ user.initials }}
          </div>
          <span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ user.name }}</span>
          <svg class="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 transition-transform duration-200" :class="open && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          class="absolute right-0 mt-2 w-52 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg overflow-hidden z-50"
          role="menu"
        >
          <div class="flex items-center gap-3 px-4 py-3 border-b border-slate-100 dark:border-slate-700">
            <div class="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
              {{ user.initials }}
            </div>
            <div class="min-w-0">
              <div class="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{{ user.name }}</div>
              <div class="text-xs text-slate-400 dark:text-slate-500 truncate">{{ user.email }}</div>
            </div>
          </div>
          <div class="py-1">
            <a href="/profile" class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors" role="menuitem" @click="open = false">
              <svg class="w-4 h-4 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
              </svg>
              Meu Perfil
            </a>
            <a href="/settings" class="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors" role="menuitem" @click="open = false">
              <svg class="w-4 h-4 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              Configurações
            </a>
            <div class="border-t border-slate-100 dark:border-slate-700 my-1"></div>

            <!-- Theme toggle -->
            <button @click="themeOpen = !themeOpen" class="flex items-center justify-between w-full px-4 py-2.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors" role="menuitem">
              <span class="flex items-center gap-2.5">
                <svg class="w-4 h-4 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 7.66l-.71-.71M4.05 4.05l-.71-.71M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                </svg>
                Tema
              </span>
              <svg class="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 transition-transform duration-200" :class="themeOpen && 'rotate-180'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            <div x-show="themeOpen" x-transition class="px-4 pb-2.5">
              <div class="flex rounded-lg bg-slate-100 dark:bg-slate-700 p-0.5">
                <button
                  @click="setTheme('light')"
                  :class="theme === 'light' ? 'bg-white dark:bg-slate-600 shadow-sm text-slate-800 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'"
                  class="flex-1 flex items-center justify-center gap-1 rounded-md py-1.5 text-xs font-medium transition-all cursor-pointer"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 7.66l-.71-.71M4.05 4.05l-.71-.71M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                  </svg>
                  Claro
                </button>
                <button
                  @click="setTheme('dark')"
                  :class="theme === 'dark' ? 'bg-white dark:bg-slate-600 shadow-sm text-slate-800 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'"
                  class="flex-1 flex items-center justify-center gap-1 rounded-md py-1.5 text-xs font-medium transition-all cursor-pointer"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                  </svg>
                  Escuro
                </button>
                <button
                  @click="setTheme('auto')"
                  :class="theme === 'auto' ? 'bg-white dark:bg-slate-600 shadow-sm text-slate-800 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'"
                  class="flex-1 flex items-center justify-center gap-1 rounded-md py-1.5 text-xs font-medium transition-all cursor-pointer"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                  </svg>
                  Auto
                </button>
              </div>
            </div>

            <div class="border-t border-slate-100 dark:border-slate-700 my-1"></div>
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

<!-- CONTENT -->
<main class="max-w-7xl mx-auto px-6 py-8">
  {% block section_title %}{% endblock %}
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
    {% block grid_items %}{% endblock %}
  </div>
</main>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dark_mode.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Run all tests to confirm no regression**

Run: `pytest tests/ -v`
Expected: 13 PASS (8 existing + 5 new).

- [ ] **Step 6: Commit**

```bash
git add app/templates/grid_page.html tests/test_dark_mode.py
git commit -m "feat: add theme toggle to user dropdown with dark mode classes"
```

---

### Task 3: Dark variant classes on card templates

**Files:**
- Modify: `app/templates/home.html`
- Modify: `app/templates/collections.html`
- Modify: `tests/test_dark_mode.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_dark_mode.py`:

```python
def test_home_cards_have_dark_classes():
    response = client.get("/")
    assert "dark:bg-slate-800" in response.text
    assert "dark:border-slate-700" in response.text


def test_collections_cards_have_dark_classes():
    response = client.get("/projects/1")
    assert "dark:bg-slate-800" in response.text
    assert "dark:border-slate-700" in response.text


def test_home_section_title_has_dark_class():
    response = client.get("/")
    assert "dark:text-slate-100" in response.text


def test_collections_section_title_has_dark_class():
    response = client.get("/projects/1")
    assert "dark:text-slate-100" in response.text
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `pytest tests/test_dark_mode.py::test_home_cards_have_dark_classes tests/test_dark_mode.py::test_home_section_title_has_dark_class -v`
Expected: FAIL — home.html cards and title have no dark classes yet.

Note: `test_collections_cards_have_dark_classes` and `test_collections_section_title_has_dark_class` may already pass because `grid_page.html` (updated in Task 2) contains `dark:bg-slate-800` and `dark:text-slate-100` in the header/dropdown. That's fine — the tests still verify the correct behavior.

- [ ] **Step 3: Update `app/templates/home.html`**

Replace the entire file with:

```html
{% extends "grid_page.html" %}

{% block title %}Home{% endblock %}

{% block section_title %}
<h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-6">Projetos</h1>
{% endblock %}

{% block grid_items %}
{% for project in projects %}
<a href="/projects/{{ project.id }}" class="bg-white dark:bg-slate-800 rounded-xl overflow-hidden shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow cursor-pointer block">
  <div class="aspect-video bg-slate-200 dark:bg-slate-700 overflow-hidden">
    {% if project.thumbnail_url %}
    <img src="{{ project.thumbnail_url }}" alt="{{ project.name }}" class="w-full h-full object-cover">
    {% else %}
    <div class="w-full h-full {{ project.placeholder_color }}"></div>
    {% endif %}
  </div>
  <div class="p-3">
    <span class="text-sm font-medium text-slate-800 dark:text-slate-100">{{ project.name }}</span>
  </div>
</a>
{% endfor %}
{% endblock %}
```

- [ ] **Step 4: Update `app/templates/collections.html`**

Replace the entire file with:

```html
{% extends "grid_page.html" %}

{% block title %}{{ project.name }}{% endblock %}

{% block page_title %}
<span class="text-sm font-semibold text-slate-800 dark:text-slate-100">{{ project.name }}</span>
{% endblock %}

{% block section_title %}
<h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-6">Coleções</h1>
{% endblock %}

{% block grid_items %}
{% for collection in collections %}
<div class="bg-white dark:bg-slate-800 rounded-xl overflow-hidden shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow cursor-pointer block">
  <div class="aspect-video bg-slate-200 dark:bg-slate-700 overflow-hidden">
    {% if collection.thumbnail_url %}
    <img src="{{ collection.thumbnail_url }}" alt="{{ collection.name }}" class="w-full h-full object-cover">
    {% else %}
    <div class="w-full h-full {{ collection.placeholder_color }}"></div>
    {% endif %}
  </div>
  <div class="p-3">
    <span class="text-sm font-medium text-slate-800 dark:text-slate-100">{{ collection.name }}</span>
  </div>
</div>
{% endfor %}
{% endblock %}
```

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: 17 PASS (8 existing + 9 new dark mode tests).

- [ ] **Step 6: Commit**

```bash
git add app/templates/home.html app/templates/collections.html tests/test_dark_mode.py
git commit -m "feat: add dark mode variant classes to card templates"
```

---

## Verification

```bash
make dev
```

1. Open `http://localhost:8000/` — defaults to Auto (matches OS preference)
2. Open dropdown → click "Tema" → panel expands with 3 pill options, "Auto" highlighted
3. Click "Escuro" → page goes dark immediately, "Escuro" highlighted
4. Click "Claro" → page goes light, "Claro" highlighted
5. Click "Auto" → follows OS, "Auto" highlighted
6. Refresh page → theme persists from `localStorage`
7. Navigate to `/projects/1` → dark mode applies consistently on collections screen
8. Change OS preference while on Auto → page reacts in real time
