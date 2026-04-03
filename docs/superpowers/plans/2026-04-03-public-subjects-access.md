# Public Subjects Access — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make public subjects accessible without login, with read-only library for non-owners, and a landing page with search for unauthenticated visitors.

**Architecture:** Add `get_optional_user` dependency that returns `None` instead of redirecting. Convert 3 GET routes to use it. Pass `is_owner` flag to templates. Wrap owner-only UI elements in `{% if is_owner %}` conditionals. Add landing page template + search endpoint.

**Tech Stack:** FastAPI, Jinja2, HTMX, Alpine.js, Tailwind CSS, SQLite

---

### Task 1: Add `get_optional_user` to auth.py

**Files:**
- Modify: `app/auth.py:55-69`

- [ ] **Step 1: Add `get_optional_user` function**

Add after the existing `get_current_user` function (after line 69):

```python
async def get_optional_user(request: Request, db) -> dict | None:
    """Like get_current_user but returns None instead of redirecting when not authenticated."""
    return await get_current_user(request, db)
```

Note: `get_current_user` already returns `None` when there's no valid session. The function is an alias for clarity — `require_auth` is the one that raises `AuthRedirect`. This distinct name makes the intent explicit in route signatures.

- [ ] **Step 2: Add import in main.py**

In `app/main.py`, add `get_optional_user` to the import from `app.auth`:

```python
from app.auth import (
    SESSION_COOKIE,
    create_session,
    destroy_session,
    get_current_user,
    get_optional_user,
    hash_password,
    oauth,
    PROVIDERS,
    set_session_cookie,
    validate_username,
    verify_password,
)
```

- [ ] **Step 3: Verify the app still starts**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -c "from app.auth import get_optional_user; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/auth.py app/main.py
git commit -m "feat: add get_optional_user auth dependency"
```

---

### Task 2: Convert `GET /` to support landing page

**Files:**
- Modify: `app/main.py:337-339`
- Create: `app/templates/landing.html`

- [ ] **Step 1: Update the `/` route**

Replace the current `home` route (lines 337-339):

```python
@app.get("/")
async def home(request: Request, user=Depends(require_auth)):
    return RedirectResponse(f"/{user['username']}", status_code=303)
```

With:

```python
@app.get("/")
async def home(request: Request, db=Depends(get_db)):
    user = await get_optional_user(request, db)
    if user:
        return RedirectResponse(f"/{user['username']}", status_code=303)
    cursor = await db.execute(
        """SELECT s.id, s.name, s.shortname, s.image_path, u.username
           FROM subjects s JOIN users u ON s.owner_id = u.id
           WHERE s.is_public = 1
           ORDER BY s.created_at DESC
           LIMIT 50""",
    )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"subjects": subjects},
    )
```

- [ ] **Step 2: Create `landing.html` template**

Create `app/templates/landing.html`:

```html
{% extends "base.html" %}

{% block title %}Resumiu{% endblock %}

{% block content %}
<!-- Header -->
<header class="sticky top-0 z-40 bg-gradient-to-r from-slate-200/60 via-slate-100/30 to-slate-200/60 dark:from-neutral-950/60 dark:via-neutral-900/30 dark:to-neutral-950/60 backdrop-blur-md border-b border-slate-300 dark:border-neutral-800 shadow-sm transition-colors">
  <div class="w-full px-6 h-[72px] flex items-center justify-between">
    <a href="/" class="flex-shrink-0">
      <img src="/static/resumiu-header.svg" alt="Logo" class="h-14 w-auto">
    </a>
    <div class="flex items-center gap-3">
      <a href="/login" class="px-4 py-2 rounded-full text-sm font-medium text-slate-700 dark:text-neutral-300 hover:bg-slate-100 dark:hover:bg-neutral-700 transition-colors">Entrar</a>
      <a href="/register" class="px-4 py-2 rounded-full text-sm font-medium text-white bg-teal-500 hover:bg-teal-600 transition-colors">Criar conta</a>
    </div>
  </div>
</header>

<main class="w-full px-6 py-8 max-w-5xl mx-auto">
  <!-- Search -->
  <div class="mb-8">
    <input
      type="text"
      name="q"
      placeholder="Buscar assuntos..."
      hx-get="/htmx/search"
      hx-trigger="input changed delay:300ms, search"
      hx-target="#search-results"
      hx-swap="innerHTML"
      class="w-full px-5 py-3 rounded-xl border border-slate-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-slate-700 dark:text-neutral-300 placeholder-slate-400 dark:placeholder-neutral-500 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 transition-colors"
    >
  </div>

  <!-- Results grid -->
  <div id="search-results" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
    {% include "partials/subject_cards.html" %}
  </div>
</main>
{% endblock %}
```

- [ ] **Step 3: Create `partials/subject_cards.html` partial**

Create `app/templates/partials/subject_cards.html`:

```html
{% set gradients = [
  "bg-gradient-to-br from-teal-200 to-purple-300 dark:from-teal-900 dark:to-purple-950",
  "bg-gradient-to-br from-blue-200 to-pink-300 dark:from-blue-900 dark:to-pink-950",
  "bg-gradient-to-br from-purple-200 to-amber-200 dark:from-purple-900 dark:to-amber-950",
  "bg-gradient-to-br from-rose-200 to-sky-300 dark:from-rose-900 dark:to-sky-950",
  "bg-gradient-to-br from-amber-200 to-teal-300 dark:from-amber-900 dark:to-teal-950",
  "bg-gradient-to-br from-emerald-200 to-indigo-300 dark:from-emerald-900 dark:to-indigo-950",
  "bg-gradient-to-br from-cyan-200 to-rose-300 dark:from-cyan-900 dark:to-rose-950",
  "bg-gradient-to-br from-indigo-200 to-emerald-300 dark:from-indigo-900 dark:to-emerald-950",
] %}
{% if subjects %}
{% for subject in subjects %}
<div class="bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-sm border border-slate-200 dark:border-neutral-700 hover:shadow-md transition-shadow">
  <a href="/{{ subject.username }}/{{ subject.shortname }}" class="block aspect-video bg-slate-200 dark:bg-neutral-700 overflow-hidden">
    {% if subject.image_path %}
    <img src="/midias/{{ subject.image_path }}" alt="{{ subject.name }}" class="w-full h-full object-cover">
    {% else %}
    <div class="w-full h-full {{ gradients[subject.id % 8] }}"></div>
    {% endif %}
  </a>
  <a href="/{{ subject.username }}/{{ subject.shortname }}" class="block p-3 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors">
    <span class="text-sm font-medium text-slate-700 dark:text-neutral-300 truncate block">{{ subject.name }}</span>
    <span class="text-xs text-slate-400 dark:text-neutral-500">{{ subject.username }}</span>
  </a>
</div>
{% endfor %}
{% else %}
<div class="col-span-full flex flex-col items-center justify-center py-16 text-center">
  <div class="w-16 h-16 mb-4 rounded-full bg-slate-100 dark:bg-neutral-700 flex items-center justify-center">
    <svg class="w-8 h-8 text-slate-300 dark:text-neutral-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/>
    </svg>
  </div>
  <p class="text-lg font-medium text-slate-500 dark:text-neutral-400 mb-1">Nenhum assunto encontrado</p>
</div>
{% endif %}
```

- [ ] **Step 4: Verify the landing page loads**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev` (in another terminal, visit `http://localhost:8000/` while logged out)

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/templates/landing.html app/templates/partials/subject_cards.html
git commit -m "feat: landing page with public subjects for unauthenticated visitors"
```

---

### Task 3: Add `/htmx/search` endpoint

**Files:**
- Modify: `app/main.py` (add new route near the bottom, before the `/{username}` catch-all routes)

- [ ] **Step 1: Add the search route**

Add this route in `app/main.py` **before** the `/{username}` route (i.e., in the HTMX routes section, around line 1078+):

```python
@app.get("/htmx/search")
async def htmx_search(request: Request, q: str = "", db=Depends(get_db)):
    q = q.strip()
    if q:
        cursor = await db.execute(
            """SELECT s.id, s.name, s.shortname, s.image_path, u.username
               FROM subjects s JOIN users u ON s.owner_id = u.id
               WHERE s.is_public = 1 AND s.name LIKE ?
               ORDER BY s.created_at DESC
               LIMIT 50""",
            (f"%{q}%",),
        )
    else:
        cursor = await db.execute(
            """SELECT s.id, s.name, s.shortname, s.image_path, u.username
               FROM subjects s JOIN users u ON s.owner_id = u.id
               WHERE s.is_public = 1
               ORDER BY s.created_at DESC
               LIMIT 50""",
        )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="partials/subject_cards.html",
        context={"subjects": subjects},
    )
```

**Important:** This route must be defined **before** the `/{username}` route in the file, otherwise FastAPI will match `htmx` as a username. Place it right after the other `/htmx/*` routes.

- [ ] **Step 2: Verify search works**

Visit landing page, type in search box, verify results update via HTMX.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add /htmx/search endpoint for public subject search"
```

---

### Task 4: Convert `GET /{username}` to support public access

**Files:**
- Modify: `app/main.py:342-364`
- Modify: `app/templates/home.html`

- [ ] **Step 1: Update the `/{username}` route**

Replace the current `user_subjects` route (lines 342-364):

```python
@app.get("/{username}")
async def user_subjects(request: Request, username: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    profile_user = await row.fetchone()
    if not profile_user:
        raise HTTPException(status_code=404)
    cursor = await db.execute(
        "SELECT id, name, shortname, image_path, is_public, created_at FROM subjects WHERE owner_id = ? ORDER BY created_at DESC",
        (profile_user["id"],),
    )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=_ctx(request, {
            "user": user,
            "subjects": subjects,
            "shortname_pattern": SHORTNAME_RE.pattern,
            "shortname_min": SHORTNAME_MIN,
            "shortname_max": SHORTNAME_MAX,
            "max_image_size": MAX_IMAGE_SIZE,
        }),
    )
```

With:

```python
@app.get("/{username}")
async def user_subjects(request: Request, username: str, db=Depends(get_db)):
    user = await get_optional_user(request, db)
    row = await db.execute("SELECT id, username FROM users WHERE username = ?", (username,))
    profile_user = await row.fetchone()
    if not profile_user:
        raise HTTPException(status_code=404)
    is_owner = user is not None and user["id"] == profile_user["id"]
    if is_owner:
        cursor = await db.execute(
            "SELECT id, name, shortname, image_path, is_public, created_at FROM subjects WHERE owner_id = ? ORDER BY created_at DESC",
            (profile_user["id"],),
        )
    else:
        cursor = await db.execute(
            "SELECT id, name, shortname, image_path, is_public, created_at FROM subjects WHERE owner_id = ? AND is_public = 1 ORDER BY created_at DESC",
            (profile_user["id"],),
        )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=_ctx(request, {
            "user": user,
            "is_owner": is_owner,
            "profile_username": profile_user["username"],
            "subjects": subjects,
            "shortname_pattern": SHORTNAME_RE.pattern,
            "shortname_min": SHORTNAME_MIN,
            "shortname_max": SHORTNAME_MAX,
            "max_image_size": MAX_IMAGE_SIZE,
        }),
    )
```

- [ ] **Step 2: Update `home.html` — wrap owner-only UI in conditionals**

In `app/templates/home.html`, wrap the "Novo Assunto" button (lines 9-14) in an `is_owner` check:

Replace:
```html
{% block section_title %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-bold text-slate-700 dark:text-neutral-300">Assuntos</h1>
  {{ btn_pill(
    label='Novo Assunto',
    icon='<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>',
    click="$dispatch('open-subject-modal')"
  ) }}
</div>
{% endblock %}
```

With:
```html
{% block section_title %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-bold text-slate-700 dark:text-neutral-300">Assuntos</h1>
  {% if is_owner %}
  {{ btn_pill(
    label='Novo Assunto',
    icon='<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>',
    click="$dispatch('open-subject-modal')"
  ) }}
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 3: Wrap the edit button on each card**

In `home.html`, wrap the edit button (lines 41-49) in an `is_owner` check:

Replace:
```html
    <!-- Edit button -->
    <button
      @click.prevent="$dispatch('open-subject-modal', { id: {{ subject.id }}, name: '{{ subject.name | e }}', shortname: '{{ subject.shortname }}', image_path: '{{ subject.image_path or '' }}', is_public: {{ 'true' if subject.is_public else 'false' }} })"
      title="Editar assunto"
      class="absolute top-2 right-2 {{ BTN_WH }} flex items-center justify-center rounded-full bg-white/50 hover:bg-white/70 text-slate-700 dark:bg-black/40 dark:hover:bg-black/60 dark:text-white transition-colors cursor-pointer backdrop-blur-sm"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
      </svg>
    </button>
```

With:
```html
    {% if is_owner %}
    <!-- Edit button -->
    <button
      @click.prevent="$dispatch('open-subject-modal', { id: {{ subject.id }}, name: '{{ subject.name | e }}', shortname: '{{ subject.shortname }}', image_path: '{{ subject.image_path or '' }}', is_public: {{ 'true' if subject.is_public else 'false' }} })"
      title="Editar assunto"
      class="absolute top-2 right-2 {{ BTN_WH }} flex items-center justify-center rounded-full bg-white/50 hover:bg-white/70 text-slate-700 dark:bg-black/40 dark:hover:bg-black/60 dark:text-white transition-colors cursor-pointer backdrop-blur-sm"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
      </svg>
    </button>
    {% endif %}
```

- [ ] **Step 4: Fix the card link to use `profile_username` instead of `user.username`**

The card links currently use `user.username`, but when a visitor views another user's profile, `user` may be `None`. Replace all occurrences of `user.username` in card hrefs.

Replace (two occurrences in the card — line 33 and line 51):
```html
    <a href="/{{ user.username }}/{{ subject.shortname }}" class="block aspect-video
```
With:
```html
    <a href="/{{ profile_username }}/{{ subject.shortname }}" class="block aspect-video
```

And:
```html
  <a href="/{{ user.username }}/{{ subject.shortname }}" class="flex items-center gap-2 p-3
```
With:
```html
  <a href="/{{ profile_username }}/{{ subject.shortname }}" class="flex items-center gap-2 p-3
```

- [ ] **Step 5: Update the empty state message for non-owners**

Replace the empty state block (lines 66-74):
```html
<div class="col-span-full flex flex-col items-center justify-center py-16 text-center">
  <div class="w-16 h-16 mb-4 rounded-full bg-slate-100 dark:bg-neutral-700 flex items-center justify-center">
    <svg class="w-8 h-8 text-slate-300 dark:text-neutral-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0118 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"/>
    </svg>
  </div>
  <p class="text-lg font-medium text-slate-500 dark:text-neutral-400 mb-1">Nenhum assunto ainda</p>
  <p class="text-sm text-slate-400 dark:text-neutral-500">Crie seu primeiro assunto para começar a organizar seus estudos.</p>
</div>
```

With:
```html
<div class="col-span-full flex flex-col items-center justify-center py-16 text-center">
  <div class="w-16 h-16 mb-4 rounded-full bg-slate-100 dark:bg-neutral-700 flex items-center justify-center">
    <svg class="w-8 h-8 text-slate-300 dark:text-neutral-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0118 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"/>
    </svg>
  </div>
  {% if is_owner %}
  <p class="text-lg font-medium text-slate-500 dark:text-neutral-400 mb-1">Nenhum assunto ainda</p>
  <p class="text-sm text-slate-400 dark:text-neutral-500">Crie seu primeiro assunto para começar a organizar seus estudos.</p>
  {% else %}
  <p class="text-lg font-medium text-slate-500 dark:text-neutral-400 mb-1">Nenhum assunto público</p>
  {% endif %}
</div>
```

- [ ] **Step 6: Wrap the subject modal in `is_owner` check**

In `home.html`, wrap the entire `{% block extra_content %}` modal block (lines 78-381):

Replace:
```html
{% block extra_content %}
<!-- Subject Modal -->
```

With:
```html
{% block extra_content %}
{% if is_owner %}
<!-- Subject Modal -->
```

And before `{% endblock %}` at line 381, add `{% endif %}`:

Replace:
```html
</div>
{% endblock %}
```

With:
```html
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 7: Fix the shortname preview in modal**

In the modal, the shortname preview (line 347) references `user.username`. Since the modal is only shown when `is_owner` is true, `user` will always exist. But update it to use `profile_username` for consistency:

Replace:
```html
            <p x-show="error_field !== 'shortname'" class="mt-1 text-[11px] text-slate-400 dark:text-neutral-500">exemplo: /{{ user.username }}/<strong x-text="shortname || 'nome-curto'"></strong></p>
```

With:
```html
            <p x-show="error_field !== 'shortname'" class="mt-1 text-[11px] text-slate-400 dark:text-neutral-500">exemplo: /{{ profile_username }}/<strong x-text="shortname || 'nome-curto'"></strong></p>
```

- [ ] **Step 8: Update header.html to handle missing user**

The header template (`partials/header.html`) assumes `user` exists (uses `user.initials`, `user.name`, `user.email`). When visiting a public page without login, `user` is `None`. Wrap the user menu section in a conditional.

In `app/templates/partials/header.html`, replace the user menu section (lines 17-161):

Replace:
```html
    <!-- User menu (right) — Pinemix Dropdown -->
    <div class="flex justify-end">
      <div
        class="relative inline-block"
        x-data="{ open: false }"
```

With:
```html
    <!-- User menu (right) -->
    <div class="flex justify-end">
      {% if user %}
      <div
        class="relative inline-block"
        x-data="{ open: false }"
```

And before the closing `</div>` of the flex-justify-end container (just before line 161's `</div>`), add the `{% else %}` branch:

Replace:
```html
      </div>
    </div>

  </div>
</header>
```

With:
```html
      </div>
      {% else %}
      <div class="flex items-center gap-3">
        <a href="/login" class="px-4 py-2 rounded-full text-sm font-medium text-slate-700 dark:text-neutral-300 hover:bg-slate-100 dark:hover:bg-neutral-700 transition-colors">Entrar</a>
        <a href="/register" class="px-4 py-2 rounded-full text-sm font-medium text-white bg-teal-500 hover:bg-teal-600 transition-colors">Criar conta</a>
      </div>
      {% endif %}
    </div>

  </div>
</header>
```

- [ ] **Step 9: Verify public access to `/{username}`**

Log out and visit `http://localhost:8000/{username}` — should show public subjects only, no edit buttons.

- [ ] **Step 10: Commit**

```bash
git add app/main.py app/templates/home.html app/templates/partials/header.html
git commit -m "feat: public access to /{username} with read-only view for non-owners"
```

---

### Task 5: Convert `GET /{username}/{shortname}` to support public access

**Files:**
- Modify: `app/main.py:524-572`
- Modify: `app/templates/topics.html`
- Modify: `app/templates/partials/library_item.html`

- [ ] **Step 1: Update the `/{username}/{shortname}` route**

Replace the current `subject_topics` route (lines 524-572):

```python
@app.get("/{username}/{shortname}")
async def subject_topics(request: Request, username: str, shortname: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute(
```

With:

```python
@app.get("/{username}/{shortname}")
async def subject_topics(request: Request, username: str, shortname: str, db=Depends(get_db)):
    user = await get_optional_user(request, db)
    row = await db.execute(
```

And after the `if not subject:` check (after line 537), add the public/owner check:

Replace:
```python
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    topics = parse_topics_json(subject["content_json"])
```

With:
```python
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    # Determine ownership
    owner_row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    owner_user = await owner_row.fetchone()
    is_owner = user is not None and owner_user is not None and user["id"] == owner_user["id"]
    # Private subjects are only visible to the owner
    if not subject["is_public"] and not is_owner:
        raise HTTPException(status_code=404)
    topics = parse_topics_json(subject["content_json"])
```

And update the template context to include `is_owner`:

Replace:
```python
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context=_ctx(request, {
            "user": user,
            "subject": subject,
            "topics": topics,
            "username": username,
            "shortname": shortname,
            "library_items": library_items,
        }),
    )
```

With:
```python
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context=_ctx(request, {
            "user": user,
            "is_owner": is_owner,
            "subject": subject,
            "topics": topics,
            "username": username,
            "shortname": shortname,
            "library_items": library_items,
        }),
    )
```

- [ ] **Step 2: Update `topics.html` — wrap owner-only controls in library drawer header**

In `app/templates/topics.html`, the library drawer header (around line 166-213) has add/reclassify buttons. Wrap them:

Replace the add + reclassify buttons block (lines 168-189):
```html
        <div class="flex items-center gap-1">
          {{ btn_icon(
            icon='<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>',
            bg='bg-teal-500 hover:bg-teal-600 border border-teal-600 dark:border-teal-400 shadow-lg',
            text_color='text-white',
            extra_class='flex-shrink-0',
            title='Adicionar conteúdo',
            click='$dispatch(\'open-add-modal\')'
          ) }}
          <button
            hx-post="/htmx/library/reclassify-all/{{ subject.id }}"
            hx-target="#library-items-list"
            hx-swap="innerHTML"
            hx-confirm="Isso vai apagar todos os tópicos e reclassificar toda a biblioteca. Continuar?"
            class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white dark:bg-neutral-700 hover:bg-amber-100 dark:hover:bg-amber-900/50 border border-slate-400/50 dark:border-neutral-600/50 text-slate-500 dark:text-neutral-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors cursor-pointer"
            title="Reclassificar toda a biblioteca"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
        </div>
```

With:
```html
        <div class="flex items-center gap-1">
          {% if is_owner %}
          {{ btn_icon(
            icon='<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>',
            bg='bg-teal-500 hover:bg-teal-600 border border-teal-600 dark:border-teal-400 shadow-lg',
            text_color='text-white',
            extra_class='flex-shrink-0',
            title='Adicionar conteúdo',
            click='$dispatch(\'open-add-modal\')'
          ) }}
          <button
            hx-post="/htmx/library/reclassify-all/{{ subject.id }}"
            hx-target="#library-items-list"
            hx-swap="innerHTML"
            hx-confirm="Isso vai apagar todos os tópicos e reclassificar toda a biblioteca. Continuar?"
            class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white dark:bg-neutral-700 hover:bg-amber-100 dark:hover:bg-amber-900/50 border border-slate-400/50 dark:border-neutral-600/50 text-slate-500 dark:text-neutral-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors cursor-pointer"
            title="Reclassificar toda a biblioteca"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
          {% endif %}
        </div>
```

- [ ] **Step 3: Wrap the add-modal include and delete-confirm modal**

In `topics.html`, wrap the library add modal include (line 342) and the confirm delete modal (lines 344-424):

Replace:
```html
{% include "partials/library_add_modal.html" %}

<!-- Confirm Delete Modal (Pinemix) -->
```

With:
```html
{% if is_owner %}
{% include "partials/library_add_modal.html" %}

<!-- Confirm Delete Modal (Pinemix) -->
```

And at the end of the delete modal (before `{% endblock %}` at line 425):

Replace:
```html
</div>
{% endblock %}
```

With:
```html
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Update `library_item.html` — wrap delete/retry buttons in `is_owner`**

In `app/templates/partials/library_item.html`, wrap the delete button in grid view (lines 84-95):

Replace:
```html
      {% if not is_processing or item.status in ('pending', 'error') %}
      <!-- Delete button -->
      <div class="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <button
          @click.stop="window.dispatchEvent(new CustomEvent('confirm-delete', { detail: { id: {{ item.id }}, name: '{{ item.name | e }}' } }))"
          class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white/50 hover:bg-red-500 dark:bg-black/40 dark:hover:bg-red-500 text-slate-700 dark:text-white hover:text-white transition-colors cursor-pointer backdrop-blur-sm"
          title="Excluir"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>
      </div>
      {% endif %}
```

With:
```html
      {% if is_owner and (not is_processing or item.status in ('pending', 'error')) %}
      <!-- Delete button -->
      <div class="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <button
          @click.stop="window.dispatchEvent(new CustomEvent('confirm-delete', { detail: { id: {{ item.id }}, name: '{{ item.name | e }}' } }))"
          class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white/50 hover:bg-red-500 dark:bg-black/40 dark:hover:bg-red-500 text-slate-700 dark:text-white hover:text-white transition-colors cursor-pointer backdrop-blur-sm"
          title="Excluir"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>
      </div>
      {% endif %}
```

Also wrap the error retry button in grid view (line 59-64). Replace the retry button inside the error overlay:

Replace:
```html
        <button
          hx-post="/htmx/library/{{ item.id }}/retry"
          hx-swap="outerHTML"
          hx-target="#library-item-{{ item.id }}"
          class="mt-1 px-3 py-1 rounded-lg text-xs font-semibold text-white bg-white/20 hover:bg-white/30 backdrop-blur-sm transition-colors cursor-pointer"
        >Tentar novamente</button>
```

With:
```html
        {% if is_owner %}
        <button
          hx-post="/htmx/library/{{ item.id }}/retry"
          hx-swap="outerHTML"
          hx-target="#library-item-{{ item.id }}"
          class="mt-1 px-3 py-1 rounded-lg text-xs font-semibold text-white bg-white/20 hover:bg-white/30 backdrop-blur-sm transition-colors cursor-pointer"
        >Tentar novamente</button>
        {% endif %}
```

For the list view (lines 156-188), wrap the retry+delete buttons block and the standalone delete button:

Replace:
```html
      {% if is_processing and item.status == 'error' %}
      <!-- Retry + Delete for error -->
      <div class="flex-shrink-0 pr-2 flex items-center gap-1">
        <button
          hx-post="/htmx/library/{{ item.id }}/retry"
          hx-swap="outerHTML"
          hx-target="#library-item-{{ item.id }}"
          @click.stop
          class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-slate-100 hover:bg-teal-500 dark:bg-neutral-700 dark:hover:bg-teal-500 text-slate-500 dark:text-neutral-400 hover:text-white transition-colors cursor-pointer"
          title="Tentar novamente"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        </button>
        <button
          @click.stop="window.dispatchEvent(new CustomEvent('confirm-delete', { detail: { id: {{ item.id }}, name: '{{ item.name | e }}' } }))"
          class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white/50 hover:bg-red-500 dark:bg-black/40 dark:hover:bg-red-500 text-slate-700 dark:text-white hover:text-white transition-colors cursor-pointer backdrop-blur-sm"
          title="Excluir"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>
      </div>
      {% elif not is_processing or item.status == 'pending' %}
      <!-- Delete button -->
      <div class="flex-shrink-0 pr-2">
        <button
          @click.stop="window.dispatchEvent(new CustomEvent('confirm-delete', { detail: { id: {{ item.id }}, name: '{{ item.name | e }}' } }))"
          class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white/50 hover:bg-red-500 dark:bg-black/40 dark:hover:bg-red-500 text-slate-700 dark:text-white hover:text-white transition-colors cursor-pointer backdrop-blur-sm"
          title="Excluir"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>
      </div>
      {% endif %}
```

With:
```html
      {% if is_owner %}
      {% if is_processing and item.status == 'error' %}
      <!-- Retry + Delete for error -->
      <div class="flex-shrink-0 pr-2 flex items-center gap-1">
        <button
          hx-post="/htmx/library/{{ item.id }}/retry"
          hx-swap="outerHTML"
          hx-target="#library-item-{{ item.id }}"
          @click.stop
          class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-slate-100 hover:bg-teal-500 dark:bg-neutral-700 dark:hover:bg-teal-500 text-slate-500 dark:text-neutral-400 hover:text-white transition-colors cursor-pointer"
          title="Tentar novamente"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        </button>
        <button
          @click.stop="window.dispatchEvent(new CustomEvent('confirm-delete', { detail: { id: {{ item.id }}, name: '{{ item.name | e }}' } }))"
          class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white/50 hover:bg-red-500 dark:bg-black/40 dark:hover:bg-red-500 text-slate-700 dark:text-white hover:text-white transition-colors cursor-pointer backdrop-blur-sm"
          title="Excluir"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>
      </div>
      {% elif not is_processing or item.status == 'pending' %}
      <!-- Delete button -->
      <div class="flex-shrink-0 pr-2">
        <button
          @click.stop="window.dispatchEvent(new CustomEvent('confirm-delete', { detail: { id: {{ item.id }}, name: '{{ item.name | e }}' } }))"
          class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white/50 hover:bg-red-500 dark:bg-black/40 dark:hover:bg-red-500 text-slate-700 dark:text-white hover:text-white transition-colors cursor-pointer backdrop-blur-sm"
          title="Excluir"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>
      </div>
      {% endif %}
      {% endif %}
```

- [ ] **Step 5: Verify public access to a public subject**

Log out and visit `http://localhost:8000/{username}/{shortname}` for a public subject — should see topics + read-only library.

- [ ] **Step 6: Verify private subject returns 404 for non-owner**

Log out and try to visit a private subject — should get 404.

- [ ] **Step 7: Commit**

```bash
git add app/main.py app/templates/topics.html app/templates/partials/library_item.html
git commit -m "feat: public access to /{username}/{shortname} with read-only library"
```

---

### Task 6: Verify ownership on all write routes

**Files:**
- Modify: `app/main.py` (audit write routes)

- [ ] **Step 1: Audit all write routes for ownership checks**

Check each write route in `app/main.py` to confirm it verifies ownership. The routes to audit:

1. `POST /htmx/subjects` (line 367) — uses `user["id"]` as `owner_id` in INSERT. OK.
2. `PUT /htmx/subjects/{subject_id}` (line 421) — queries `WHERE id = ? AND owner_id = ?`. OK.
3. `DELETE /htmx/subjects/{subject_id}` (line 487) — queries `WHERE id = ? AND owner_id = ?`. OK.
4. `POST /htmx/library/preview` (line 584) — queries `WHERE id = ? AND owner_id = ?`. OK.
5. `POST /htmx/library/save` (line 758) — needs to verify.
6. `DELETE /htmx/library/{item_id}` (line 738) — needs to verify.
7. `POST /htmx/library/{item_id}/classify` (line 839) — needs to verify.
8. `POST /htmx/library/{item_id}/retry` (line 975) — needs to verify.
9. `POST /htmx/library/reclassify-all/{subject_id}` (line 1011) — needs to verify.
10. `GET /htmx/library/{item_id}/status` (line 936) — needs to verify.

Read each of these routes and verify they check ownership. If any are missing the check, add it.

- [ ] **Step 2: Fix any missing ownership checks**

For each route that operates on a `library_item`, the ownership check pattern should be:

```python
# Verify the library item belongs to a subject owned by the user
row = await db.execute(
    """SELECT li.id FROM library_items li
       JOIN subjects s ON li.subject_id = s.id
       WHERE li.id = ? AND s.owner_id = ?""",
    (item_id, user["id"]),
)
if not await row.fetchone():
    raise HTTPException(status_code=404)
```

For routes that operate on a `subject_id`, verify with:
```python
row = await db.execute(
    "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
    (subject_id, user["id"]),
)
if not await row.fetchone():
    raise HTTPException(status_code=404)
```

- [ ] **Step 3: Commit if changes were needed**

```bash
git add app/main.py
git commit -m "fix: ensure all write routes verify ownership"
```

---

### Task 7: Final verification

- [ ] **Step 1: Test landing page**

1. Log out
2. Visit `/` — should see landing page with public subjects and search bar
3. Type in search box — results should filter via HTMX
4. Click a subject card — should navigate to the subject detail page

- [ ] **Step 2: Test public profile page**

1. While logged out, visit `/{username}` — should show only public subjects
2. Log in as that user, visit `/{username}` — should show all subjects with edit controls

- [ ] **Step 3: Test public subject detail**

1. While logged out, visit `/{username}/{public-shortname}` — should show topics + library (read-only)
2. Verify no add/delete/reclassify buttons visible
3. Verify library items are clickable and open the viewer modal
4. Visit `/{username}/{private-shortname}` while logged out — should get 404

- [ ] **Step 4: Test owner access unchanged**

1. Log in as the owner
2. Visit `/{username}/{shortname}` — all controls should work as before
3. Add/delete library items, reclassify — everything should function normally

- [ ] **Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "fix: address issues found during manual verification"
```
