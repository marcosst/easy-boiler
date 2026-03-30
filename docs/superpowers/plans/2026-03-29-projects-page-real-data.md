# Projects Page — Real Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mock projects page with real database queries, restructure routes to `/{username}`, and seed test data for `marcos@medire.com.br`.

**Architecture:** New dbmate migration adds `image_path` column and seeds 5 projects. Route `GET /` redirects to `/{username}`. Route `GET /{username}` queries the DB for that user's projects and renders them. Template uses gradient palette indexed by project ID.

**Tech Stack:** FastAPI, aiosqlite, dbmate, Jinja2, Tailwind CSS

---

## File Structure

- **Create:** `db/migrations/YYYYMMDDHHMMSS_add_image_path_and_seed_projects.sql` — migration with `image_path` column + seed data
- **Modify:** `app/main.py:383-389` — replace home route, add `/{username}` route, mount midias
- **Modify:** `app/templates/home.html` — dynamic gradients, image support, updated links
- **Modify:** `Makefile:9` — add `mkdir -p midias` to setup target
- **Modify:** `tests/conftest.py` — add `projects` table to test schema
- **Modify:** `tests/test_home.py` — update tests for new route behavior

---

### Task 1: Create the dbmate migration

**Files:**
- Create: `db/migrations/<timestamp>_add_image_path_and_seed_projects.sql`

- [ ] **Step 1: Generate the migration file**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && DATABASE_URL=sqlite:///$(pwd)/data/app.db dbmate new add_image_path_and_seed_projects
```

- [ ] **Step 2: Write the migration SQL**

Edit the generated file to contain:

```sql
-- migrate:up
ALTER TABLE projects ADD COLUMN image_path TEXT;

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Reforma Apartamento 302', 'reforma-apartamento-302', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Orcamento Obra Centro', 'orcamento-obra-centro', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Residencial Vila Nova', 'residencial-vila-nova', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Projeto Fachada Comercial', 'projeto-fachada-comercial', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Levantamento Terreno Sul', 'levantamento-terreno-sul', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

-- migrate:down
DELETE FROM projects WHERE shortname IN (
    'reforma-apartamento-302',
    'orcamento-obra-centro',
    'residencial-vila-nova',
    'projeto-fachada-comercial',
    'levantamento-terreno-sul'
);

-- SQLite 3.35+ supports ALTER TABLE DROP COLUMN
ALTER TABLE projects DROP COLUMN image_path;
```

- [ ] **Step 3: Run the migration**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && DATABASE_URL=sqlite:///$(pwd)/data/app.db dbmate up
```

Expected: migration applies without errors. Verify with:
```bash
cd /home/ubuntu/aaaa/easy-boiler && sqlite3 data/app.db "SELECT id, name, shortname FROM projects;"
```

Expected: 5 rows with the seeded project names (only if user marcos exists in the DB).

- [ ] **Step 4: Commit**

```bash
git add db/migrations/*_add_image_path_and_seed_projects.sql db/schema.sql
git commit -m "feat: add image_path column to projects and seed test data"
```

---

### Task 2: Mount midias directory and update Makefile

**Files:**
- Modify: `app/main.py:31` (add mount after static mount)
- Modify: `Makefile:9` (add mkdir -p midias)
- Create: `midias/.gitkeep` (to track the empty directory)

- [ ] **Step 1: Create midias directory and .gitkeep**

Run:
```bash
mkdir -p /home/ubuntu/aaaa/easy-boiler/midias && touch /home/ubuntu/aaaa/easy-boiler/midias/.gitkeep
```

- [ ] **Step 2: Add midias mount in main.py**

In `app/main.py`, after line 31 (`app.mount("/static", ...)`), add:

```python
app.mount("/midias", StaticFiles(directory="midias"), name="midias")
```

- [ ] **Step 3: Update Makefile setup target**

In `Makefile`, change the setup target from:
```makefile
setup:
	uv sync
	cp -n .env.example .env || true
	mkdir -p data
```
to:
```makefile
setup:
	uv sync
	cp -n .env.example .env || true
	mkdir -p data midias
```

- [ ] **Step 4: Verify the app starts**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && timeout 5 uv run python -c "from app.main import app; print('OK')" || true
```

Expected: `OK` (or import succeeds without error)

- [ ] **Step 5: Commit**

```bash
git add app/main.py Makefile midias/.gitkeep
git commit -m "feat: mount midias directory for project images"
```

---

### Task 3: Update test schema and conftest for projects table

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add projects table to test SCHEMA**

In `tests/conftest.py`, add the projects table to the `SCHEMA` string, after the `oauth_accounts` table:

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
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""
```

- [ ] **Step 2: Insert test projects in the auth_client fixture**

In the `setup_db` function inside `auth_client`, after inserting the user, add 2 test projects:

```python
            await db.execute(
                "INSERT INTO projects (name, shortname, owner_id) VALUES (?, ?, ?)",
                ("Projeto Teste", "projeto-teste", 1),
            )
            await db.execute(
                "INSERT INTO projects (name, shortname, owner_id) VALUES (?, ?, ?)",
                ("Segundo Projeto", "segundo-projeto", 1),
            )
            await db.commit()
```

- [ ] **Step 3: Run existing tests to check nothing breaks yet**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/conftest.py -v 2>&1 | head -20
```

Expected: no errors (conftest is not a test file, just verify it parses)

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add projects table to test schema and seed test projects"
```

---

### Task 4: Implement route changes — `GET /` redirect and `GET /{username}`

**Files:**
- Modify: `app/main.py:383-389`

- [ ] **Step 1: Write failing tests for the new route behavior**

Replace `tests/test_home.py` with:

```python
def test_home_redirects_to_username(auth_client):
    response = auth_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/testuser"


def test_username_route_returns_200(auth_client):
    response = auth_client.get("/testuser")
    assert response.status_code == 200


def test_username_route_contains_projetos_title(auth_client):
    response = auth_client.get("/testuser")
    assert "Projetos" in response.text


def test_username_route_contains_user_name(auth_client):
    response = auth_client.get("/testuser")
    assert "testuser" in response.text


def test_username_route_shows_db_projects(auth_client):
    response = auth_client.get("/testuser")
    assert "Projeto Teste" in response.text
    assert "Segundo Projeto" in response.text


def test_username_route_unknown_user_returns_404(auth_client):
    response = auth_client.get("/nobody")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/test_home.py -v 2>&1
```

Expected: most tests FAIL (old route returns 200 with mock data, redirect not implemented yet)

- [ ] **Step 3: Implement the route changes in main.py**

Replace the `home` route (lines 383-389) with:

```python
@app.get("/")
async def home(request: Request, user=Depends(require_auth)):
    return RedirectResponse(f"/{user['username']}", status_code=303)


@app.get("/{username}")
async def user_projects(request: Request, username: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    profile_user = await row.fetchone()
    if not profile_user:
        raise HTTPException(status_code=404)
    cursor = await db.execute(
        "SELECT id, name, shortname, image_path, created_at FROM projects WHERE owner_id = ? ORDER BY created_at DESC",
        (profile_user["id"],),
    )
    projects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": user, "projects": projects},
    )
```

**Important:** The `/{username}` route must be registered AFTER all fixed routes (`/login`, `/register`, `/logout`, `/auth/*`, `/htmx/*`, `/projects/*`). Since it's placed at the end of the "Protected routes" section, and FastAPI matches routes in order, fixed routes will take precedence.

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/test_home.py -v 2>&1
```

Expected: all 6 tests PASS

- [ ] **Step 5: Run all tests to check for regressions**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/ -v 2>&1
```

Expected: all tests pass. The test `test_home_redirects_to_login_when_unauthenticated` in `test_auth.py` should still pass since `/` still requires auth and redirects to `/login`.

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_home.py
git commit -m "feat: replace mock home route with /{username} DB-backed projects page"
```

---

### Task 5: Update template — dynamic gradients, image support, updated links

**Files:**
- Modify: `app/templates/home.html`

- [ ] **Step 1: Update home.html with gradient palette and image support**

Replace the full content of `app/templates/home.html` with:

```html
{% extends "grid_page.html" %}

{% block title %}Home{% endblock %}

{% block section_title %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-bold text-slate-800 dark:text-neutral-100">Projetos</h1>
  <button class="h-10 flex items-center gap-2 px-4 rounded-full bg-teal-500 hover:bg-teal-600 text-white border border-teal-600 dark:border-teal-400 shadow-lg transition-colors cursor-pointer">
    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
    </svg>
    <span class="text-sm font-bold uppercase tracking-wider">Novo Projeto</span>
  </button>
</div>
{% endblock %}

{% set gradients = [
  "bg-gradient-to-br from-teal-400 to-teal-700",
  "bg-gradient-to-br from-blue-400 to-blue-700",
  "bg-gradient-to-br from-purple-400 to-purple-700",
  "bg-gradient-to-br from-rose-400 to-rose-700",
  "bg-gradient-to-br from-amber-400 to-amber-700",
  "bg-gradient-to-br from-emerald-400 to-emerald-700",
  "bg-gradient-to-br from-cyan-400 to-cyan-700",
  "bg-gradient-to-br from-indigo-400 to-indigo-700",
] %}

{% block grid_items %}
{% for project in projects %}
<div class="bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-sm border border-slate-200 dark:border-neutral-700 hover:shadow-md transition-shadow" x-data="{ menu: false }">
  <div class="relative">
    <a href="/{{ user.username }}/{{ project.shortname }}" class="block aspect-video bg-slate-200 dark:bg-neutral-700 overflow-hidden">
      {% if project.image_path %}
      <img src="/midias/{{ project.image_path }}" alt="{{ project.name }}" class="w-full h-full object-cover">
      {% else %}
      <div class="w-full h-full {{ gradients[project.id % 8] }}"></div>
      {% endif %}
    </a>
    <!-- 3-dot menu -->
    <div class="absolute top-2 right-2">
      <button @click.prevent="menu = !menu" class="w-7 h-7 flex items-center justify-center rounded-full bg-black/40 hover:bg-black/60 text-white transition-colors cursor-pointer backdrop-blur-sm">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z"/>
        </svg>
      </button>
      <div
        x-show="menu"
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
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
          </svg>
          Renomear
        </button>
        <button @click="menu = false" class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
          <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
          </svg>
          Trocar imagem
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
  <a href="/{{ user.username }}/{{ project.shortname }}" class="block p-3">
    <span class="text-sm font-medium text-slate-800 dark:text-neutral-100">{{ project.name }}</span>
  </a>
</div>
{% endfor %}
{% endblock %}
```

Key changes from original:
1. `{% set gradients = [...] %}` — 8-color palette
2. `{{ gradients[project.id % 8] }}` instead of `{{ project.placeholder_color }}`
3. `{% if project.image_path %}` shows `<img src="/midias/...">` when set
4. Links changed from `/projects/{{ project.id }}` to `/{{ user.username }}/{{ project.shortname }}`

- [ ] **Step 2: Run tests to verify everything still passes**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/test_home.py -v 2>&1
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add app/templates/home.html
git commit -m "feat: update projects template with dynamic gradients and image support"
```

---

### Task 6: Update test_auth.py for new redirect behavior

**Files:**
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Check if the unauthenticated redirect test still passes**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/test_auth.py::test_home_redirects_to_login_when_unauthenticated -v 2>&1
```

The test expects `GET /` to redirect to `/login` when unauthenticated. Since `GET /` now redirects to `/{username}` when authenticated (which still requires auth via `require_auth`), the unauthenticated behavior should be unchanged — it should still redirect to `/login`.

Expected: PASS (no changes needed)

- [ ] **Step 2: Run full test suite**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && uv run pytest tests/ -v 2>&1
```

Expected: all tests PASS

- [ ] **Step 3: Commit (only if changes were needed)**

Only commit if any test fixes were required.

---

### Task 7: Manual verification

- [ ] **Step 1: Run migrations and start the dev server**

Run:
```bash
cd /home/ubuntu/aaaa/easy-boiler && make migrate
```

Then:
```bash
cd /home/ubuntu/aaaa/easy-boiler && make dev
```

- [ ] **Step 2: Verify in the browser**

1. Open `http://localhost:8000/` — should redirect to `/marcos` (or whatever the username is for marcos@medire.com.br)
2. The projects page should show 5 cards with colored gradients
3. Each card should link to `/marcos/<shortname>`
4. The 3-dot menu should appear on hover

- [ ] **Step 3: Final commit if any fixes needed**

Only commit if manual testing revealed issues that needed fixing.
