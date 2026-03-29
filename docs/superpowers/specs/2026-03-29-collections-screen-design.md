# Collections Screen Design

## Context

The home screen displays a grid of projects. Clicking a project should navigate to a Collections screen that shows the collections belonging to that project. The layout must be consistent with the home screen (same grid structure, same header style), and the project name must appear centered in the header.

To avoid duplication, a shared `grid_page.html` base template will be extracted so both the home and collections screens inherit the same layout.

## Template Architecture

```
base.html
  └── grid_page.html        ← new shared base
        ├── home.html       ← refactored to extend grid_page
        └── collections.html ← new
```

### `grid_page.html` (new)

Extends `base.html`. Defines the shared layout:

- **Header** (dark background, matching current home header):
  - Left: logo linked to `/`
  - Center: `{% block page_title %}` — each page provides its own title text
  - Right: user avatar with Alpine.js dropdown (Meu Perfil, Configurações, Sair)
- **Main content**: responsive 3-column grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`)
  - `{% block grid_items %}` — each page provides its own cards
- **Blocks exposed**: `title`, `page_title`, `grid_items`

### `home.html` (refactored)

- Extends `grid_page.html` instead of `base.html`
- `page_title` block: empty (logo alone, as today)
- `grid_items` block: existing project cards (no visual change)

### `collections.html` (new)

- Extends `grid_page.html`
- `page_title` block: `{{ project.name }}`
- `grid_items` block: collection cards — same structure as project cards (aspect-video thumbnail or placeholder gradient, collection name below)

## Route

`GET /projects/{project_id}` in `app/main.py`:

- Looks up project by ID in `MOCK_PROJECTS`; returns 404 if not found
- Injects context: `project`, `user` (from `MOCK_USER`), `collections` (from `MOCK_COLLECTIONS[project_id]`)
- Returns `TemplateResponse("collections.html", ...)`

## Mock Data

Add `MOCK_COLLECTIONS` dict in `main.py`, keyed by project ID. Each project has 6 collections:

```python
MOCK_COLLECTIONS = {
    1: [
        {"id": 1, "name": "Coleção 1", "thumbnail_url": None, "placeholder_color": "from-blue-400 to-blue-600"},
        ...
    ],
    ...
}
```

Each collection: `id`, `name`, `thumbnail_url` (None), `placeholder_color` (Tailwind gradient classes).

## Navigation

- Project cards in `home.html` already link to `/projects/{{ project.id }}` — no change needed
- Logo in header links to `/` on both screens

## Verification

1. `make dev` — server starts on :8000
2. Open `http://localhost:8000/` — home screen renders unchanged (projects grid, logo, avatar)
3. Click any project card — navigates to `/projects/{id}`
4. Collections screen shows: logo left, project name centered in header, avatar right, 6 collection cards in grid
5. Click logo — returns to home screen
6. Direct URL `/projects/999` — returns 404
