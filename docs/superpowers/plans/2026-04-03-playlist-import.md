# Playlist Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to import multiple videos from a YouTube playlist at once in the library add modal.

**Architecture:** Add a `fetch_playlist_videos()` function to `app/services/apify_service.py` that calls the same Apify actor with `downloadSubtitles=false`. Modify the preview route to detect playlist URLs and pass an `is_playlist` flag. Add a new `/htmx/library/playlist-videos` route that returns a list of videos with checkboxes. Modify the save route to accept bulk video submissions.

**Tech Stack:** FastAPI, HTMX, Alpine.js, Jinja2, Apify API (streamers/youtube-scraper), httpx

---

### Task 1: Add `fetch_playlist_videos()` to apify_service.py

**Files:**
- Modify: `app/services/apify_service.py`

This function calls the Apify actor with the playlist URL and `downloadSubtitles=false`, returning a list of video metadata dicts.

- [ ] **Step 1: Add the function to apify_service.py**

Add this function at the end of `app/services/apify_service.py`:

```python
async def fetch_playlist_videos(playlist_url: str) -> list[dict]:
    """Fetch video list from a YouTube playlist via Apify (no subtitles).

    Returns list of {"video_id": str, "title": str, "thumbnail_url": str}.
    """
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        raise ValueError("Erro interno inesperado.")

    actor_id = os.getenv("APIFY_YOUTUBE_SCRAPER_ACTOR_ID", "streamers/youtube-scraper").strip()
    actor_id = actor_id or "streamers/youtube-scraper"
    actor_path = actor_id.replace("/", "~")
    api_url = f"https://api.apify.com/v2/acts/{actor_path}/run-sync-get-dataset-items?token={token}"

    timeout_raw = os.getenv("APIFY_YOUTUBE_TIMEOUT_SECS", "180").strip()
    try:
        timeout_secs = int(timeout_raw)
    except ValueError:
        timeout_secs = 180
    if timeout_secs <= 0:
        timeout_secs = 180

    payload = {
        "startUrls": [{"url": playlist_url}],
        "downloadSubtitles": False,
        "maxResults": 200,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_secs) as client:
            resp = await client.post(
                api_url,
                json=payload,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            items = resp.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError("Falha ao buscar vídeos da playlist. Tente novamente.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Falha ao buscar vídeos da playlist. Tente novamente.") from exc
    except Exception as exc:
        raise RuntimeError("A Apify retornou uma resposta inválida.") from exc

    if not isinstance(items, list) or not items:
        raise RuntimeError("Nenhum vídeo encontrado na playlist.")

    videos = []
    for item in items:
        video_id = item.get("id") or ""
        title = item.get("title") or f"Vídeo {video_id}"
        thumbnail_url = item.get("thumbnailUrl") or ""
        if not thumbnail_url and video_id:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        if video_id:
            videos.append({
                "video_id": video_id,
                "title": title,
                "thumbnail_url": thumbnail_url,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

    return videos
```

- [ ] **Step 2: Verify the function is importable**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -c "from app.services.apify_service import fetch_playlist_videos; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/services/apify_service.py
git commit -m "feat: add fetch_playlist_videos to apify_service"
```

---

### Task 2: Modify preview route to detect playlist URLs

**Files:**
- Modify: `app/main.py:645-740` (the `htmx_library_preview` route, youtube branch)

Detect `list=` parameter in the URL. If present with `v=`, pass `is_playlist=True` and `playlist_url` to the template. If only `list=` (no `v=`), fetch the playlist videos and return the playlist videos partial directly.

- [ ] **Step 1: Add import for `fetch_playlist_videos` and `parse_qs`/`urlparse`**

At the top of `app/main.py`, add to existing imports:

```python
from urllib.parse import parse_qs, urlparse
```

And update the apify import:

```python
from app.services.apify_service import fetch_playlist_videos
```

- [ ] **Step 2: Add a helper to extract playlist_id from URL**

Add this right after the `YOUTUBE_RE` definition (around line 638):

```python
def _extract_playlist_id(url: str) -> str | None:
    """Return the playlist ID from a YouTube URL, or None."""
    parsed = urlparse(url)
    list_ids = parse_qs(parsed.query).get("list", [])
    return list_ids[0] if list_ids else None
```

- [ ] **Step 3: Add a helper to find existing video URLs in a subject**

Add right after the previous helper:

```python
async def _get_existing_video_ids(db, subject_id: int) -> set[str]:
    """Return set of YouTube video_ids already in the subject's library."""
    rows = await db.execute_fetchall(
        "SELECT url FROM library_items WHERE subject_id = ? AND type = 'youtube' AND deleted_at IS NULL",
        (subject_id,),
    )
    existing = set()
    for row in rows:
        m = YOUTUBE_RE.search(row["url"] or "")
        if m:
            existing.add(m.group(1))
    return existing
```

- [ ] **Step 4: Modify the youtube branch of the preview route**

The existing `YOUTUBE_RE` regex only matches URLs with `v=`. For playlist-only URLs (`youtube.com/playlist?list=XYZ`), `m` will be `None`, so we need to handle playlist-only URLs before the regex fails. Replace the entire youtube branch from `if not url:` (line 668) through the final return (line 739):

```python
        if not url:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Informe a URL do vídeo."}),
            )

        playlist_id = _extract_playlist_id(url)

        # Playlist-only URL (no video): go straight to playlist video list
        m = YOUTUBE_RE.search(url)
        if not m and playlist_id:
            try:
                videos = await fetch_playlist_videos(url)
            except (ValueError, RuntimeError) as exc:
                return templates.TemplateResponse(
                    request=request,
                    name="partials/library_preview.html",
                    context=_ctx(request, {"error": str(exc)}),
                )
            existing_ids = await _get_existing_video_ids(db, subject_id)
            for v in videos:
                v["existing"] = v["video_id"] in existing_ids
            new_count = sum(1 for v in videos if not v["existing"])
            return templates.TemplateResponse(
                request=request,
                name="partials/library_playlist_videos.html",
                context=_ctx(request, {
                    "videos": videos,
                    "subject_id": subject_id,
                    "playlist_url": url,
                    "new_count": new_count,
                    "total_count": len(videos),
                    "playlist_only": True,
                }),
            )

        if not m:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "URL do YouTube inválida."}),
            )
        video_id = m.group(1)

        # Check if video already exists in user's library
        dup = await db.execute(
            "SELECT id FROM library_items WHERE url = ? AND subject_id = ? AND deleted_at IS NULL",
            (url, subject_id),
        )
        if await dup.fetchone():
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Este vídeo já existe na biblioteca."}),
            )

        # Fetch title via oEmbed
        title = None
        try:
            oembed_resp = httpx.get(
                "https://noembed.com/embed",
                params={"url": f"https://www.youtube.com/watch?v={video_id}"},
                timeout=10,
            )
            oembed_resp.raise_for_status()
            title = oembed_resp.json().get("title")
        except Exception:
            pass

        if not title:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Não foi possível encontrar este vídeo no YouTube."}),
            )

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
                "is_playlist": bool(playlist_id),
                "playlist_url": url if playlist_id else None,
            }),
        )
```

- [ ] **Step 5: Verify syntax**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -c "import app.main; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add app/main.py
git commit -m "feat: detect playlist URLs in preview route"
```

---

### Task 3: Add `/htmx/library/playlist-videos` route

**Files:**
- Modify: `app/main.py` (add new route after the preview route)

This route is called when the user checks the "Incluir vídeos da playlist" checkbox. It fetches the playlist videos via Apify and returns the list partial.

- [ ] **Step 1: Add the route**

Add this route in `app/main.py` right after the closing of the preview route (after the `elif type == "pdf":` block's return, before the `@app.delete` route):

```python
@app.post("/htmx/library/playlist-videos")
async def htmx_library_playlist_videos(
    request: Request,
    url: str = Form(...),
    subject_id: int = Form(...),
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

    try:
        videos = await fetch_playlist_videos(url)
    except (ValueError, RuntimeError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="partials/library_preview.html",
            context=_ctx(request, {"error": str(exc)}),
        )

    existing_ids = await _get_existing_video_ids(db, subject_id)
    for v in videos:
        v["existing"] = v["video_id"] in existing_ids
    new_count = sum(1 for v in videos if not v["existing"])

    return templates.TemplateResponse(
        request=request,
        name="partials/library_playlist_videos.html",
        context=_ctx(request, {
            "videos": videos,
            "subject_id": subject_id,
            "playlist_url": url,
            "new_count": new_count,
            "total_count": len(videos),
            "playlist_only": False,
        }),
    )
```

- [ ] **Step 2: Verify syntax**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -c "import app.main; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add playlist-videos HTMX route"
```

---

### Task 4: Modify the save route for bulk insert

**Files:**
- Modify: `app/main.py` (the `htmx_library_save` route at line 819)

Add a new route for bulk saving playlist videos alongside the existing single-item save.

- [ ] **Step 1: Add bulk save route**

Add this route right after the existing `/htmx/library/save` route:

```python
@app.post("/htmx/library/save-playlist")
async def htmx_library_save_playlist(
    request: Request,
    subject_id: int = Form(...),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    form = await request.form()
    urls = form.getlist("urls[]")
    names = form.getlist("names[]")
    thumbnail_urls = form.getlist("thumbnail_urls[]")

    if not urls:
        return Response(status_code=422, content="Nenhum vídeo selecionado.")

    # Verify subject belongs to user
    row = await db.execute(
        "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404)

    username = user["username"]

    # Get next position
    row = await db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM library_items WHERE subject_id = ?",
        (subject_id,),
    )
    next_pos = (await row.fetchone())["next_pos"]

    items_html = []
    for i, url in enumerate(urls):
        name = names[i] if i < len(names) else f"Vídeo {i + 1}"
        name = name.strip() or f"Vídeo {i + 1}"
        thumb_url = thumbnail_urls[i] if i < len(thumbnail_urls) else ""

        # Extract video_id for thumbnail
        m = YOUTUBE_RE.search(url)
        video_id = m.group(1) if m else None

        # Download thumbnail locally
        image_path = None
        if video_id:
            thumb_dir = Path("midias") / username / "thumbnails"
            thumb_dir.mkdir(parents=True, exist_ok=True)
            thumb_filename = f"{uuid.uuid4().hex}.jpg"
            try:
                thumb_resp = httpx.get(
                    f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                    timeout=10,
                )
                thumb_resp.raise_for_status()
                (thumb_dir / thumb_filename).write_bytes(thumb_resp.content)
                image_path = f"{username}/thumbnails/{thumb_filename}"
            except Exception:
                pass

        cursor = await db.execute(
            """INSERT INTO library_items (subject_id, name, type, url, file_path, image_path, position, status)
               VALUES (?, ?, 'youtube', ?, NULL, ?, ?, 'pending')""",
            (subject_id, name, url, image_path, next_pos + i),
        )
        item_id = cursor.lastrowid

        # Enqueue background processing
        async with get_queue_db() as queue_db:
            await enqueue(queue_db, item_id)

        item = {
            "id": item_id,
            "name": name,
            "type": "youtube",
            "url": url,
            "file_path": None,
            "image_path": image_path,
            "status": "pending",
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg" if video_id else None,
        }
        item_resp = templates.TemplateResponse(
            request=request,
            name="partials/library_item.html",
            context=_ctx(request, {"item": item, "is_owner": True}),
        )
        items_html.append(item_resp.body.decode())

    await db.commit()

    response = Response(
        content="".join(items_html),
        media_type="text/html",
    )
    response.headers["HX-Trigger-After-Settle"] = json.dumps({"close-add-modal": True})
    return response
```

- [ ] **Step 2: Verify syntax**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -c "import app.main; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add bulk save-playlist route"
```

---

### Task 5: Update `library_preview.html` for playlist checkbox

**Files:**
- Modify: `app/templates/partials/library_preview.html`

When `is_playlist` is true, add the checkbox below the thumbnail. The checkbox triggers an HTMX request to load the playlist videos list.

- [ ] **Step 1: Update the non-error form in library_preview.html**

In `app/templates/partials/library_preview.html`, in the non-error form (the `{% else %}` block starting at line 44), add the playlist checkbox after the thumbnail and before the name input. Also wrap the form content in a div that can be hidden when playlist mode is active.

Replace the entire `{% else %}` block (lines 44-80) with:

```html
{% else %}
<div id="single-preview-area">
<form hx-post="/htmx/library/save"
      hx-target="#library-items-list" hx-swap="beforeend"
      @htmx:before-request="saving = true; $el.closest('.rounded-2xl')?.scrollTo(0,0)"
      @htmx:after-request="saving = false">
  <input type="hidden" name="subject_id" value="{{ subject_id }}">
  <input type="hidden" name="type" value="{{ preview_type }}">
  {% if preview_type == 'youtube' %}
  <input type="hidden" name="url" value="{{ preview_url }}">
  {% elif preview_type == 'pdf' %}
  <input type="hidden" name="file_path" value="{{ preview_file_path }}">
  {% endif %}
  <input type="hidden" name="image_path" value="{{ preview_image_path or '' }}">

  <!-- Thumbnail -->
  {% if preview_image_path %}
  <div class="aspect-video rounded-lg overflow-hidden bg-slate-100 dark:bg-neutral-800 mb-3">
    <img src="/midias/{{ preview_image_path }}" alt="Preview" class="w-full h-full object-cover">
  </div>
  {% endif %}

  {% if is_playlist %}
  <!-- Playlist checkbox -->
  <label class="flex items-center gap-2 p-2.5 rounded-lg bg-slate-50 dark:bg-neutral-700/50 border border-slate-200 dark:border-neutral-600 mb-3 cursor-pointer select-none"
         hx-post="/htmx/library/playlist-videos"
         hx-target="#playlist-videos-area"
         hx-swap="innerHTML"
         hx-vals='{"url": "{{ playlist_url }}", "subject_id": "{{ subject_id }}"}'
         hx-trigger="click[event.target.closest('label') && !document.querySelector('#playlist-videos-area').children.length]"
         hx-indicator="#playlist-spinner"
         @click="playlistMode = !playlistMode"
         x-show="!playlistMode">
    <input type="checkbox" class="w-4 h-4 rounded border-slate-300 dark:border-neutral-600 text-teal-500 focus:ring-teal-500 cursor-pointer" x-model="playlistMode" @click.stop>
    <span class="text-sm text-slate-600 dark:text-neutral-300 font-medium">Incluir vídeos da playlist</span>
  </label>
  {% endif %}

  <div x-show="!playlistMode">
    <!-- Editable name -->
    <div class="mb-4">
      <label class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1">Nome</label>
      <input type="text" name="name" value="{{ preview_name }}"
             class="w-full rounded-lg border border-slate-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
             required>
    </div>

    <!-- Save button -->
    <button type="submit" :disabled="saving"
            class="w-full h-10 rounded-lg bg-teal-500 hover:bg-teal-600 text-white text-sm font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
      <span x-show="!saving">Salvar na biblioteca</span>
      <span x-show="saving" x-cloak>Salvando...</span>
    </button>
  </div>
</form>
</div>

{% if is_playlist %}
<!-- Skeleton loader for playlist videos -->
<div id="playlist-spinner" class="htmx-indicator mt-3 space-y-2">
  {% for _ in range(5) %}
  <div class="flex items-center gap-2 p-2 animate-pulse">
    <div class="w-4 h-4 bg-slate-200 dark:bg-neutral-700 rounded"></div>
    <div class="w-14 h-8 bg-slate-200 dark:bg-neutral-700 rounded"></div>
    <div class="flex-1 h-4 bg-slate-200 dark:bg-neutral-700 rounded"></div>
  </div>
  {% endfor %}
</div>
{% endif %}

<!-- Playlist videos area (HTMX target) -->
<div id="playlist-videos-area" x-show="playlistMode"></div>

{% endif %}
```

- [ ] **Step 2: Verify template renders without errors**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('app/templates'))
t = env.get_template('partials/library_preview.html')
print('OK')
"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/library_preview.html
git commit -m "feat: add playlist checkbox to library preview"
```

---

### Task 6: Create `library_playlist_videos.html` partial

**Files:**
- Create: `app/templates/partials/library_playlist_videos.html`

This is the list of videos with checkboxes, the master checkbox, counter, and save button.

- [ ] **Step 1: Create the template**

Create `app/templates/partials/library_playlist_videos.html`:

```html
<div x-data="{
    selectAll: true,
    toggleAll() {
        this.selectAll = !this.selectAll;
        this.$refs.videoList.querySelectorAll('input[type=checkbox]:not(:disabled)').forEach(cb => {
            cb.checked = this.selectAll;
        });
    },
    get selectedCount() {
        return this.$refs.videoList ? this.$refs.videoList.querySelectorAll('input[type=checkbox]:checked').length : 0;
    }
}">
  <!-- Master checkbox -->
  <div class="flex items-center gap-2 p-2.5 rounded-lg border mb-3"
       :class="selectAll ? 'bg-teal-50 dark:bg-teal-900/20 border-teal-500' : 'bg-slate-50 dark:bg-neutral-700/50 border-slate-200 dark:border-neutral-600'">
    {% if not playlist_only %}
    <input type="checkbox" checked
           class="w-4 h-4 rounded border-slate-300 dark:border-neutral-600 text-teal-500 focus:ring-teal-500 cursor-pointer"
           @click="toggleAll()">
    {% else %}
    <input type="checkbox" checked disabled
           class="w-4 h-4 rounded border-slate-300 dark:border-neutral-600 text-teal-500 focus:ring-teal-500 opacity-50">
    {% endif %}
    <span class="text-sm font-medium" :class="selectAll ? 'text-teal-600 dark:text-teal-400' : 'text-slate-600 dark:text-neutral-300'">Incluir vídeos da playlist</span>
    <span class="text-xs ml-auto" :class="selectAll ? 'text-teal-500 dark:text-teal-400' : 'text-slate-400 dark:text-neutral-500'"
          x-text="selectedCount + ' de {{ total_count }} selecionados'"></span>
  </div>

  <!-- Video list -->
  <form hx-post="/htmx/library/save-playlist"
        hx-target="#library-items-list" hx-swap="beforeend"
        @htmx:before-request="saving = true; $el.closest('.rounded-2xl')?.scrollTo(0,0)"
        @htmx:after-request="saving = false">
    <input type="hidden" name="subject_id" value="{{ subject_id }}">

    <div x-ref="videoList" class="max-h-[280px] overflow-y-auto space-y-1.5 mb-3 dark-scrollbar">
      {% for video in videos %}
      {% if video.existing %}
      <!-- Existing item (greyed out, no checkbox) -->
      <div class="flex items-center gap-2 p-2 rounded-lg bg-slate-50/50 dark:bg-neutral-800/30 border border-slate-100 dark:border-neutral-800 opacity-50">
        <div class="w-4 h-4 flex-shrink-0"></div>
        <div class="w-14 h-8 flex-shrink-0 rounded overflow-hidden bg-slate-200 dark:bg-neutral-700">
          {% if video.thumbnail_url %}
          <img src="{{ video.thumbnail_url }}" alt="" class="w-full h-full object-cover">
          {% endif %}
        </div>
        <span class="text-xs text-slate-400 dark:text-neutral-500 flex-1 truncate">{{ video.title }} <span class="italic">(já na biblioteca)</span></span>
      </div>
      {% else %}
      <!-- New item (checkbox, selectable) -->
      <label class="flex items-center gap-2 p-2 rounded-lg bg-white dark:bg-neutral-800/50 border border-slate-200 dark:border-neutral-700 hover:border-teal-400 dark:hover:border-teal-600 cursor-pointer transition-colors">
        <input type="checkbox" name="urls[]" value="{{ video.url }}" checked
               class="w-4 h-4 flex-shrink-0 rounded border-slate-300 dark:border-neutral-600 text-teal-500 focus:ring-teal-500 cursor-pointer">
        <input type="hidden" name="names[]" value="{{ video.title }}">
        <input type="hidden" name="thumbnail_urls[]" value="{{ video.thumbnail_url }}">
        <div class="w-14 h-8 flex-shrink-0 rounded overflow-hidden bg-slate-100 dark:bg-neutral-700">
          {% if video.thumbnail_url %}
          <img src="{{ video.thumbnail_url }}" alt="" class="w-full h-full object-cover">
          {% endif %}
        </div>
        <span class="text-xs text-slate-700 dark:text-neutral-300 flex-1 truncate">{{ video.title }}</span>
      </label>
      {% endif %}
      {% endfor %}
    </div>

    <!-- Save button -->
    <button type="submit" :disabled="saving || selectedCount === 0"
            class="w-full h-10 rounded-lg bg-teal-500 hover:bg-teal-600 text-white text-sm font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
      <span x-show="!saving" x-text="'Salvar ' + selectedCount + ' vídeos na biblioteca'"></span>
      <span x-show="saving" x-cloak>Salvando...</span>
    </button>
  </form>
</div>
```

- [ ] **Step 2: Verify template parses**

Run: `cd /home/ubuntu/aaaa/easy-boiler && python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('app/templates'))
t = env.get_template('partials/library_playlist_videos.html')
print('OK')
"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/library_playlist_videos.html
git commit -m "feat: add playlist videos list partial template"
```

---

### Task 7: Update `library_add_modal.html` with `playlistMode` state

**Files:**
- Modify: `app/templates/partials/library_add_modal.html`

Add `playlistMode: false` to the Alpine.js `x-data` and reset it in the `reset()` function.

- [ ] **Step 1: Add `playlistMode` to x-data**

In `app/templates/partials/library_add_modal.html`, in the `x-data` object (line 3), add `playlistMode: false` after `previewed: false`:

Replace:
```javascript
    previewed: false,
```

With:
```javascript
    previewed: false,
    playlistMode: false,
```

- [ ] **Step 2: Reset `playlistMode` in the reset function**

In the `reset()` function (line 12-20), add `this.playlistMode = false;` after `this.previewed = false;`:

Replace:
```javascript
      this.previewed = false;
```

With:
```javascript
      this.previewed = false;
      this.playlistMode = false;
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/library_add_modal.html
git commit -m "feat: add playlistMode to library modal Alpine state"
```

---

### Task 8: Fix hidden input issue in playlist form

**Files:**
- Modify: `app/templates/partials/library_playlist_videos.html`

The `names[]` and `thumbnail_urls[]` hidden inputs are inside `<label>` elements that wrap checkboxes. When a checkbox is unchecked, the hidden inputs are still submitted. We need the hidden inputs to only submit for checked items. Move them to be paired with the checkbox logic.

- [ ] **Step 1: Fix hidden inputs to only submit for checked videos**

In `library_playlist_videos.html`, the hidden inputs for `names[]` and `thumbnail_urls[]` should only be submitted when their corresponding checkbox is checked. Since HTML doesn't natively support this, we'll handle it in the backend by pairing indices. Actually, a simpler approach: encode name and thumbnail_url into the checkbox value as a JSON string, and parse it server-side.

Replace the new item label block in `library_playlist_videos.html`:

```html
      <!-- New item (checkbox, selectable) -->
      <label class="flex items-center gap-2 p-2 rounded-lg bg-white dark:bg-neutral-800/50 border border-slate-200 dark:border-neutral-700 hover:border-teal-400 dark:hover:border-teal-600 cursor-pointer transition-colors">
        <input type="checkbox" name="videos[]" value='{{ {"url": video.url, "title": video.title, "thumbnail_url": video.thumbnail_url} | tojson }}' checked
               class="w-4 h-4 flex-shrink-0 rounded border-slate-300 dark:border-neutral-600 text-teal-500 focus:ring-teal-500 cursor-pointer">
        <div class="w-14 h-8 flex-shrink-0 rounded overflow-hidden bg-slate-100 dark:bg-neutral-700">
          {% if video.thumbnail_url %}
          <img src="{{ video.thumbnail_url }}" alt="" class="w-full h-full object-cover">
          {% endif %}
        </div>
        <span class="text-xs text-slate-700 dark:text-neutral-300 flex-1 truncate">{{ video.title }}</span>
      </label>
```

- [ ] **Step 2: Update the save-playlist route to parse JSON values**

In `app/main.py`, update the `htmx_library_save_playlist` route to parse the `videos[]` form field:

Replace the form parsing section:

```python
    form = await request.form()
    raw_videos = form.getlist("videos[]")

    if not raw_videos:
        return Response(status_code=422, content="Nenhum vídeo selecionado.")

    videos = []
    for raw in raw_videos:
        try:
            video = json.loads(raw)
            videos.append(video)
        except (json.JSONDecodeError, TypeError):
            continue

    if not videos:
        return Response(status_code=422, content="Nenhum vídeo selecionado.")
```

And replace the loop that processes each video:

```python
    items_html = []
    for i, video in enumerate(videos):
        url = video.get("url", "")
        name = (video.get("title") or f"Vídeo {i + 1}").strip()

        # Extract video_id for thumbnail
        m = YOUTUBE_RE.search(url)
        video_id = m.group(1) if m else None

        # Download thumbnail locally
        image_path = None
        if video_id:
            thumb_dir = Path("midias") / username / "thumbnails"
            thumb_dir.mkdir(parents=True, exist_ok=True)
            thumb_filename = f"{uuid.uuid4().hex}.jpg"
            try:
                thumb_resp = httpx.get(
                    f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                    timeout=10,
                )
                thumb_resp.raise_for_status()
                (thumb_dir / thumb_filename).write_bytes(thumb_resp.content)
                image_path = f"{username}/thumbnails/{thumb_filename}"
            except Exception:
                pass

        cursor = await db.execute(
            """INSERT INTO library_items (subject_id, name, type, url, file_path, image_path, position, status)
               VALUES (?, ?, 'youtube', ?, NULL, ?, ?, 'pending')""",
            (subject_id, name, url, image_path, next_pos + i),
        )
        item_id = cursor.lastrowid

        # Enqueue background processing
        async with get_queue_db() as queue_db:
            await enqueue(queue_db, item_id)

        item = {
            "id": item_id,
            "name": name,
            "type": "youtube",
            "url": url,
            "file_path": None,
            "image_path": image_path,
            "status": "pending",
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg" if video_id else None,
        }
        item_resp = templates.TemplateResponse(
            request=request,
            name="partials/library_item.html",
            context=_ctx(request, {"item": item, "is_owner": True}),
        )
        items_html.append(item_resp.body.decode())
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/library_playlist_videos.html app/main.py
git commit -m "fix: encode video data as JSON in checkbox values for correct form submission"
```

---

### Task 9: Manual end-to-end test

- [ ] **Step 1: Start the dev server**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`

- [ ] **Step 2: Test single video URL (no playlist)**

1. Open `http://localhost:8000`, log in, navigate to a subject
2. Click "Adicionar à Biblioteca"
3. Select YouTube, paste a single video URL (e.g., `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
4. Verify: preview shows thumbnail + name, **no** playlist checkbox
5. Save — verify item appears in library

- [ ] **Step 3: Test video+playlist URL**

1. Paste a video URL with playlist parameter (e.g., `https://www.youtube.com/watch?v=abc&list=PLxxxxxx`)
2. Verify: preview shows thumbnail + name + checkbox "Incluir vídeos da playlist" (unchecked)
3. Click save without checking the box — verify only the single video is saved
4. Repeat, but this time check the playlist box
5. Verify: skeleton loader appears, then list of videos with checkboxes
6. Verify: already-existing videos show greyed out with "(já na biblioteca)"
7. Uncheck a couple videos, click "Salvar X vídeos na biblioteca"
8. Verify: all selected videos appear in library, modal closes

- [ ] **Step 4: Test playlist-only URL**

1. Paste a playlist-only URL (e.g., `https://www.youtube.com/playlist?list=PLxxxxxx`)
2. Verify: goes directly to video list (no intermediate thumbnail preview)
3. Select some videos, save, verify they appear

- [ ] **Step 5: Test error handling**

1. Paste an invalid URL — verify error message
2. Test with a broken playlist URL — verify error message with "Tentar novamente" context

- [ ] **Step 6: Final commit**

If any fixes were needed during testing, commit them:

```bash
git add -A
git commit -m "fix: adjustments from manual playlist import testing"
```
