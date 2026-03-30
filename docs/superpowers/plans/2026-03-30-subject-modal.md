# Subject Create/Edit Modal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified Alpine.js + HTMX modal for creating, editing, and deleting subjects from the home page.

**Architecture:** The modal lives in `home.html` as an Alpine.js component. It dispatches HTMX requests to three new FastAPI routes (`POST /htmx/subjects`, `PUT /htmx/subjects/{id}`, `DELETE /htmx/subjects/{id}`). Image uploads go to `midias/` with UUID filenames. Errors return via `HX-Trigger` headers so Alpine can display them inline without re-rendering the form.

**Tech Stack:** FastAPI, Jinja2, Alpine.js, HTMX, aiosqlite, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-03-30-subject-modal-design.md`

**Note on DB schema:** The `shortname` column has a global `UNIQUE` constraint (not per-user). The uniqueness check in routes must account for this.

---

### Task 1: POST /htmx/subjects — Create subject route

**Files:**
- Modify: `app/main.py` (add route after line 297, add imports for `UploadFile`, `File`, `uuid`, `Path`)

- [ ] **Step 1: Add imports at the top of main.py**

Add these to the existing import block at the top of `app/main.py`:

```python
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, UploadFile, File
```

Note: `Form`, `Request`, `Response`, etc. are already imported. Just add `UploadFile`, `File` to the existing `from fastapi import ...` line, and add `import uuid` and `from pathlib import Path` as new lines.

- [ ] **Step 2: Add the create subject route**

Add this route in `app/main.py` after the `user_subjects` route (after line 297), before the `subject_topics` route:

```python
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

SHORTNAME_RE = re.compile(r"^[a-z0-9-]{2,}$")


@app.post("/htmx/subjects")
async def htmx_create_subject(
    request: Request,
    name: str = Form(...),
    shortname: str = Form(...),
    is_public: bool = Form(False),
    image: UploadFile | None = File(None),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    name = name.strip()
    shortname = shortname.strip().lower()

    if not name:
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "name", "message": "Informe o título do assunto."}}'},
        )

    if not SHORTNAME_RE.match(shortname):
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "shortname", "message": "Apenas letras minúsculas, números e hífens (mín. 2 caracteres)."}}'},
        )

    row = await db.execute("SELECT id FROM subjects WHERE shortname = ?", (shortname,))
    if await row.fetchone():
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "shortname", "message": "Este nome curto já está em uso. Escolha outro."}}'},
        )

    image_path = None
    if image and image.filename:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                status_code=422,
                headers={"HX-Trigger": '{"subject-error": {"field": "image", "message": "Tipo de arquivo não suportado."}}'},
            )
        contents = await image.read()
        if len(contents) > MAX_IMAGE_SIZE:
            return Response(
                status_code=422,
                headers={"HX-Trigger": '{"subject-error": {"field": "image", "message": "Arquivo muito grande (máx. 5MB)."}}'},
            )
        ext = Path(image.filename).suffix.lower() or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = Path("midias") / filename
        filepath.write_bytes(contents)
        image_path = filename

    await db.execute(
        "INSERT INTO subjects (name, shortname, is_public, owner_id, image_path) VALUES (?, ?, ?, ?, ?)",
        (name, shortname, int(is_public), user["id"], image_path),
    )
    await db.commit()

    return Response(
        status_code=204,
        headers={"HX-Redirect": f"/{user['username']}"},
    )
```

- [ ] **Step 3: Verify the server starts without errors**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`

Expected: Server starts on :8000 without import or syntax errors. Stop it after confirming.

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: add POST /htmx/subjects route for creating subjects"
```

---

### Task 2: PUT /htmx/subjects/{id} — Update subject route

**Files:**
- Modify: `app/main.py` (add route after the create route)

- [ ] **Step 1: Add the update subject route**

Add this route in `app/main.py` right after the `htmx_create_subject` route:

```python
@app.put("/htmx/subjects/{subject_id}")
async def htmx_update_subject(
    request: Request,
    subject_id: int,
    name: str = Form(...),
    shortname: str = Form(...),
    is_public: bool = Form(False),
    image: UploadFile | None = File(None),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    row = await db.execute(
        "SELECT id, shortname, image_path FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)

    name = name.strip()
    shortname = shortname.strip().lower()

    if not name:
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "name", "message": "Informe o título do assunto."}}'},
        )

    if not SHORTNAME_RE.match(shortname):
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "shortname", "message": "Apenas letras minúsculas, números e hífens (mín. 2 caracteres)."}}'},
        )

    row = await db.execute(
        "SELECT id FROM subjects WHERE shortname = ? AND id != ?",
        (shortname, subject_id),
    )
    if await row.fetchone():
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "shortname", "message": "Este nome curto já está em uso. Escolha outro."}}'},
        )

    image_path = subject["image_path"]
    if image and image.filename:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                status_code=422,
                headers={"HX-Trigger": '{"subject-error": {"field": "image", "message": "Tipo de arquivo não suportado."}}'},
            )
        contents = await image.read()
        if len(contents) > MAX_IMAGE_SIZE:
            return Response(
                status_code=422,
                headers={"HX-Trigger": '{"subject-error": {"field": "image", "message": "Arquivo muito grande (máx. 5MB)."}}'},
            )
        # Remove old image if exists
        if subject["image_path"]:
            old_path = Path("midias") / subject["image_path"]
            old_path.unlink(missing_ok=True)
        ext = Path(image.filename).suffix.lower() or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = Path("midias") / filename
        filepath.write_bytes(contents)
        image_path = filename

    await db.execute(
        "UPDATE subjects SET name = ?, shortname = ?, is_public = ?, image_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (name, shortname, int(is_public), image_path, subject_id),
    )
    await db.commit()

    return Response(
        status_code=204,
        headers={"HX-Redirect": f"/{user['username']}"},
    )
```

- [ ] **Step 2: Verify the server starts without errors**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`

Expected: Server starts on :8000 without errors. Stop it after confirming.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add PUT /htmx/subjects/{id} route for updating subjects"
```

---

### Task 3: DELETE /htmx/subjects/{id} — Delete subject route

**Files:**
- Modify: `app/main.py` (add route after the update route)

- [ ] **Step 1: Add the delete subject route**

Add this route in `app/main.py` right after the `htmx_update_subject` route:

```python
@app.delete("/htmx/subjects/{subject_id}")
async def htmx_delete_subject(
    request: Request,
    subject_id: int,
    user=Depends(require_auth),
    db=Depends(get_db),
):
    form = await request.form()
    shortname_confirm = form.get("shortname_confirm", "").strip()

    row = await db.execute(
        "SELECT id, shortname, image_path FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)

    if shortname_confirm != subject["shortname"]:
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "delete", "message": "Nome curto não confere."}}'},
        )

    if subject["image_path"]:
        old_path = Path("midias") / subject["image_path"]
        old_path.unlink(missing_ok=True)

    await db.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    await db.commit()

    return Response(
        status_code=204,
        headers={"HX-Redirect": f"/{user['username']}"},
    )
```

- [ ] **Step 2: Verify the server starts without errors**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`

Expected: Server starts on :8000 without errors. Stop it after confirming.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add DELETE /htmx/subjects/{id} route for deleting subjects"
```

---

### Task 4: Update home.html — Wire up buttons + add subject modal

**Files:**
- Modify: `app/templates/home.html`

- [ ] **Step 1: Add `is_public` to the subjects query in main.py**

The `user_subjects` route currently selects `id, name, shortname, image_path, created_at`. We need `is_public` too for the edit modal. Modify line 289 of `app/main.py`:

```python
    cursor = await db.execute(
        "SELECT id, name, shortname, image_path, is_public, created_at FROM subjects WHERE owner_id = ? ORDER BY created_at DESC",
        (profile_user["id"],),
    )
```

- [ ] **Step 2: Replace the entire home.html template**

Replace the full contents of `app/templates/home.html` with:

```html
{% extends "grid_page.html" %}

{% block title %}Home{% endblock %}

{% block section_title %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-bold text-slate-800 dark:text-neutral-100">Assuntos</h1>
  <button
    @click="$dispatch('open-subject-modal')"
    class="h-10 flex items-center gap-2 px-4 rounded-full bg-teal-500 hover:bg-teal-600 text-white border border-teal-600 dark:border-teal-400 shadow-lg transition-colors cursor-pointer"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
    </svg>
    <span class="text-sm font-bold uppercase tracking-wider">Novo Assunto</span>
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
{% for subject in subjects %}
<div class="bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-sm border border-slate-200 dark:border-neutral-700 hover:shadow-md transition-shadow" x-data="{ menu: false }">
  <div class="relative">
    <a href="/{{ user.username }}/{{ subject.shortname }}" class="block aspect-video bg-slate-200 dark:bg-neutral-700 overflow-hidden">
      {% if subject.image_path %}
      <img src="/midias/{{ subject.image_path }}" alt="{{ subject.name }}" class="w-full h-full object-cover">
      {% else %}
      <div class="w-full h-full {{ gradients[subject.id % 8] }}"></div>
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
        <button
          @click="menu = false; $dispatch('open-subject-modal', { id: {{ subject.id }}, name: '{{ subject.name | e }}', shortname: '{{ subject.shortname }}', image_path: '{{ subject.image_path or '' }}', is_public: {{ 'true' if subject.is_public else 'false' }} })"
          class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors cursor-pointer"
        >
          <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
          </svg>
          Editar
        </button>
      </div>
    </div>
  </div>
  <a href="/{{ user.username }}/{{ subject.shortname }}" class="block p-3 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors">
    <span class="text-sm font-medium text-slate-800 dark:text-neutral-100">{{ subject.name }}</span>
  </a>
</div>
{% endfor %}
{% endblock %}

{% block extra_content %}
<!-- Subject Modal -->
<div
  x-data="{
    show: false,
    id: null,
    name: '',
    shortname: '',
    shortname_dirty: false,
    is_public: false,
    image_path: '',
    image_preview: null,
    image_file: null,
    delete_confirm: '',
    error_field: '',
    error_message: '',
    submitting: false,

    get isEdit() { return this.id !== null },
    get canDelete() { return this.delete_confirm === this.shortname },

    open(detail) {
      if (detail && detail.id) {
        this.id = detail.id;
        this.name = detail.name;
        this.shortname = detail.shortname;
        this.shortname_dirty = true;
        this.is_public = detail.is_public;
        this.image_path = detail.image_path || '';
      } else {
        this.id = null;
        this.name = '';
        this.shortname = '';
        this.shortname_dirty = false;
        this.is_public = false;
        this.image_path = '';
      }
      this.image_preview = null;
      this.image_file = null;
      this.delete_confirm = '';
      this.error_field = '';
      this.error_message = '';
      this.submitting = false;
      this.show = true;
    },

    close() {
      this.show = false;
    },

    slugify(text) {
      return text
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .split(/\s+/)
        .slice(0, 3)
        .join('-')
        .replace(/[^a-z0-9-]/g, '')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
    },

    onNameInput() {
      if (!this.shortname_dirty) {
        this.shortname = this.slugify(this.name);
      }
    },

    onShortnameInput() {
      this.shortname_dirty = true;
    },

    onImageSelect(event) {
      const file = event.target.files[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        this.error_field = 'image';
        this.error_message = 'Arquivo muito grande (máx. 5MB).';
        return;
      }
      this.image_file = file;
      this.image_preview = URL.createObjectURL(file);
      this.error_field = '';
      this.error_message = '';
    },

    async submit() {
      this.error_field = '';
      this.error_message = '';

      if (!this.name.trim()) {
        this.error_field = 'name';
        this.error_message = 'Informe o título do assunto.';
        return;
      }
      if (!/^[a-z0-9-]{2,}$/.test(this.shortname)) {
        this.error_field = 'shortname';
        this.error_message = 'Apenas letras minúsculas, números e hífens (mín. 2 caracteres).';
        return;
      }

      this.submitting = true;
      const formData = new FormData();
      formData.append('name', this.name.trim());
      formData.append('shortname', this.shortname);
      formData.append('is_public', this.is_public ? 'true' : 'false');
      if (this.image_file) {
        formData.append('image', this.image_file);
      }

      const url = this.isEdit ? `/htmx/subjects/${this.id}` : '/htmx/subjects';
      const method = this.isEdit ? 'PUT' : 'POST';

      try {
        const resp = await fetch(url, { method, body: formData });
        const redirect = resp.headers.get('HX-Redirect');
        if (resp.ok && redirect) {
          window.location.href = redirect;
          return;
        }
        const trigger = resp.headers.get('HX-Trigger');
        if (trigger) {
          const parsed = JSON.parse(trigger);
          if (parsed['subject-error']) {
            this.error_field = parsed['subject-error'].field;
            this.error_message = parsed['subject-error'].message;
          }
        }
      } catch (e) {
        this.error_message = 'Erro de conexão. Tente novamente.';
      }
      this.submitting = false;
    },

    async submitDelete() {
      if (!this.canDelete) return;
      this.submitting = true;
      const formData = new FormData();
      formData.append('shortname_confirm', this.delete_confirm);

      try {
        const resp = await fetch(`/htmx/subjects/${this.id}`, { method: 'DELETE', body: formData });
        const redirect = resp.headers.get('HX-Redirect');
        if (resp.ok && redirect) {
          window.location.href = redirect;
          return;
        }
        const trigger = resp.headers.get('HX-Trigger');
        if (trigger) {
          const parsed = JSON.parse(trigger);
          if (parsed['subject-error']) {
            this.error_field = parsed['subject-error'].field;
            this.error_message = parsed['subject-error'].message;
          }
        }
      } catch (e) {
        this.error_message = 'Erro de conexão. Tente novamente.';
      }
      this.submitting = false;
    }
  }"
  @open-subject-modal.window="open($event.detail)"
  @keydown.escape.window="close()"
>
  <div x-show="show" x-cloak class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div x-show="show" @click="close()" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100" x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0" class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>

    <!-- Panel -->
    <div x-show="show" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 scale-95" x-transition:enter-end="opacity-100 scale-100" x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100 scale-100" x-transition:leave-end="opacity-0 scale-95" class="relative bg-white dark:bg-neutral-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto dark-scrollbar">
      <!-- Close button -->
      <button @click="close()" class="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-slate-100 dark:bg-neutral-700 hover:bg-slate-200 dark:hover:bg-neutral-600 transition-colors cursor-pointer">
        <svg class="w-4 h-4 text-slate-500 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>

      <div class="p-6">
        <!-- Image area 16:9 -->
        <div class="mb-5">
          <div class="relative w-full aspect-video rounded-xl overflow-hidden bg-slate-200 dark:bg-neutral-700">
            <!-- Preview image (newly selected) -->
            <template x-if="image_preview">
              <img :src="image_preview" class="w-full h-full object-cover">
            </template>
            <!-- Existing image (edit mode, no new selection) -->
            <template x-if="!image_preview && image_path">
              <img :src="'/midias/' + image_path" class="w-full h-full object-cover">
            </template>
            <!-- Gradient fallback -->
            <template x-if="!image_preview && !image_path">
              <div class="w-full h-full bg-gradient-to-br from-purple-400 to-purple-700 flex items-center justify-center">
                <svg class="w-10 h-10 text-white/60" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
              </div>
            </template>
            <!-- Upload button -->
            <button @click="$refs.imageInput.click()" type="button" class="absolute bottom-2 right-2 px-3 py-1.5 rounded-lg text-xs text-white bg-black/50 hover:bg-black/70 backdrop-blur-sm transition-colors cursor-pointer">
              <span x-text="image_preview || image_path ? 'Trocar imagem' : 'Carregar imagem'"></span>
            </button>
            <input x-ref="imageInput" type="file" accept="image/*" class="hidden" @change="onImageSelect($event)">
          </div>
          <!-- Image error -->
          <p x-show="error_field === 'image'" x-text="error_message" class="mt-1.5 text-xs text-red-500"></p>
        </div>

        <!-- Title -->
        <div class="mb-4">
          <label class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">Título</label>
          <input
            type="text"
            x-model="name"
            @input="onNameInput()"
            placeholder="Nome do assunto..."
            maxlength="100"
            class="w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-neutral-900 text-slate-800 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 transition-colors"
            :class="error_field === 'name' ? 'border-red-400 dark:border-red-500' : 'border-slate-200 dark:border-neutral-700'"
          >
          <p x-show="error_field === 'name'" x-text="error_message" class="mt-1.5 text-xs text-red-500"></p>
        </div>

        <!-- Shortname -->
        <div class="mb-4">
          <label class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5">Nome curto <span class="font-normal normal-case">(usado na URL)</span></label>
          <input
            type="text"
            x-ref="shortname"
            x-model="shortname"
            @input="onShortnameInput()"
            placeholder="nome-do-assunto"
            class="w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-neutral-900 text-slate-800 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 transition-colors"
            :class="error_field === 'shortname' ? 'border-red-400 dark:border-red-500' : 'border-slate-200 dark:border-neutral-700'"
          >
          <p x-show="error_field === 'shortname'" x-text="error_message" class="mt-1.5 text-xs text-red-500"></p>
          <p x-show="error_field !== 'shortname'" class="mt-1 text-[11px] text-slate-400 dark:text-neutral-500">exemplo: /{{ user.username }}/<strong x-text="shortname || 'nome-curto'"></strong></p>
        </div>

        <!-- Visibility toggle -->
        <div class="mb-6 flex items-center justify-between px-3.5 py-3 rounded-lg border transition-colors" :class="is_public ? 'bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-800' : 'bg-slate-50 dark:bg-neutral-900 border-slate-200 dark:border-neutral-700'">
          <div>
            <div class="text-sm font-medium text-slate-700 dark:text-neutral-200">Visibilidade</div>
            <div class="text-xs" :class="is_public ? 'text-teal-600 dark:text-teal-400' : 'text-slate-400 dark:text-neutral-500'" x-text="is_public ? 'Público — qualquer pessoa pode ver' : 'Privado — só você pode ver'"></div>
          </div>
          <button type="button" @click="is_public = !is_public" class="relative w-11 h-6 rounded-full transition-colors cursor-pointer" :class="is_public ? 'bg-teal-500' : 'bg-slate-300 dark:bg-neutral-600'">
            <div class="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform" :class="is_public ? 'translate-x-[22px]' : 'translate-x-0.5'"></div>
          </button>
        </div>

        <!-- Action buttons -->
        <div class="flex justify-end gap-3 mb-1">
          <button @click="close()" type="button" class="px-5 py-2.5 rounded-lg border border-slate-200 dark:border-neutral-700 text-sm text-slate-600 dark:text-neutral-400 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors cursor-pointer">Cancelar</button>
          <button @click="submit()" type="button" :disabled="submitting" class="px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-teal-500 hover:bg-teal-600 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
            <span x-text="isEdit ? 'Salvar' : 'Criar Assunto'"></span>
          </button>
        </div>

        <!-- Danger zone (edit only) -->
        <template x-if="isEdit">
          <div class="mt-6 pt-5 border-t border-red-200 dark:border-red-900/50">
            <div class="text-sm font-semibold text-red-600 dark:text-red-400 mb-2">Zona de perigo</div>
            <p class="text-xs text-slate-500 dark:text-neutral-400 mb-2.5">Para excluir, digite <strong class="text-slate-700 dark:text-neutral-200" x-text="shortname"></strong> abaixo:</p>
            <div class="flex gap-2.5">
              <input
                type="text"
                x-model="delete_confirm"
                placeholder="Digite o nome curto..."
                class="flex-1 px-3.5 py-2.5 rounded-lg border border-red-200 dark:border-red-900/50 text-sm bg-white dark:bg-neutral-900 text-slate-800 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-red-500/50"
              >
              <button @click="submitDelete()" type="button" :disabled="!canDelete || submitting" class="px-4 py-2.5 rounded-lg border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 text-sm font-medium text-red-600 dark:text-red-400 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed" :class="canDelete && 'hover:bg-red-100 dark:hover:bg-red-900/40'">Excluir</button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Add the `extra_content` block to grid_page.html**

The `grid_page.html` template does not have an `extra_content` block. Add one after the `</main>` tag. Edit `app/templates/grid_page.html` to add the block:

Change:
```html
</main>
{% endblock %}
```

To:
```html
</main>
{% block extra_content %}{% endblock %}
{% endblock %}
```

- [ ] **Step 4: Verify the server starts and the home page loads without errors**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`

Open `http://localhost:8000` in browser. Verify:
- The home page loads without JS errors
- Clicking "Novo Assunto" opens the modal in create mode (empty fields, no danger zone)
- Clicking the "..." → "Editar" on a subject card opens the modal in edit mode (fields filled, danger zone visible)
- The modal closes with Escape key or clicking backdrop or X button

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/templates/home.html app/templates/grid_page.html
git commit -m "feat: add subject create/edit/delete modal to home page"
```

---

### Task 5: End-to-end manual testing

**Files:** None (testing only)

- [ ] **Step 1: Test creating a subject**

1. Open `http://localhost:8000`
2. Click "Novo Assunto"
3. Type "Programação em Python Avançado" in the title
4. Verify the nome curto auto-fills as `programacao-em-python`
5. Click "Criar Assunto"
6. Verify redirect to home and new card appears

Expected: New subject card visible on home page.

- [ ] **Step 2: Test editing a subject**

1. Click "..." → "Editar" on the new subject card
2. Verify fields are pre-filled with correct data
3. Change the title to "Python Avançado"
4. Verify shortname does NOT auto-update (because `shortname_dirty` is true in edit mode)
5. Toggle visibility to public
6. Click "Salvar"
7. Verify redirect and updated data

Expected: Subject title updated on card.

- [ ] **Step 3: Test image upload**

1. Edit the subject
2. Click "Carregar imagem" / "Trocar imagem"
3. Select an image file
4. Verify preview appears in the 16:9 area
5. Click "Salvar"
6. Verify the image appears on the card on the home page

Expected: Image shows on card instead of gradient.

- [ ] **Step 4: Test duplicate shortname error**

1. Create a second subject
2. Set its shortname to the same as the first subject's shortname
3. Click "Criar Assunto"
4. Verify error message appears below the nome curto field: "Este nome curto já está em uso. Escolha outro."

Expected: Error shown inline, modal stays open.

- [ ] **Step 5: Test deleting a subject**

1. Edit a subject
2. In the danger zone, type the wrong shortname
3. Verify the "Excluir" button stays disabled (opacity 50%)
4. Type the correct shortname
5. Verify the "Excluir" button becomes enabled
6. Click "Excluir"
7. Verify redirect to home and subject card is gone

Expected: Subject deleted, card removed from grid.

- [ ] **Step 6: Commit any fixes**

If any issues were found during testing, fix them and commit:

```bash
git add -A
git commit -m "fix: address issues found during subject modal testing"
```
