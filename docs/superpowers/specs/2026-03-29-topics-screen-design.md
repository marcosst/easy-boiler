# Topics Screen Design

## Context

Third screen in the app hierarchy: Home (projects) → Collections → **Topics**. When the user clicks a collection, they see its topics organized as a 3-level accordion. Level 3 items ("Detalhes") may open a modal with a YouTube video and/or markdown text.

## Template Architecture

### Extract header to partial

The header currently lives inline in `grid_page.html`. Extract it to `partials/header.html` so both `grid_page.html` and the new `topics.html` can reuse it.

The partial receives a context variable `header_title` (raw HTML string) instead of a Jinja2 block, since includes don't support blocks. Each page sets `header_title` via `{% set %}` before the include.

| Page               | `header_title` value                                                        |
|--------------------|-----------------------------------------------------------------------------|
| `home.html`        | empty (logo only)                                                           |
| `collections.html` | `"Nome do Projeto"` (plain text)                                            |
| `topics.html`      | `"<a href='/projects/{id}'>Nome do Projeto</a> / Nome da Coleção"` (linked) |

### Updated template tree

```
base.html
  └── grid_page.html        ({% include "partials/header.html" %})
  │     ├── home.html
  │     └── collections.html
  └── topics.html            ({% include "partials/header.html" %})
```

### `partials/header.html` (new — extracted from grid_page)

Exact same header markup currently in `grid_page.html`, but replaces the `{% block page_title %}` with `{{ header_title | safe }}`. Everything else (logo left, user dropdown right, dark mode toggle) stays identical.

### `grid_page.html` (refactored)

Replace inline header with `{% include "partials/header.html" %}`. Each child template sets `header_title` via `{% set %}` in its own block. The `section_title` and `grid_items` blocks remain unchanged.

### `topics.html` (new)

Extends `base.html` directly. Structure:

1. `{% set header_title %}` — "Projeto / Coleção" with project name linked
2. `{% include "partials/header.html" %}`
3. `<main>` — accordion list (not a grid)

## Accordion — 3 Levels

Managed with Alpine.js. Multiple sections can be open simultaneously.

### Level 1 — Tópico

- `x-data="{ open: false }"` on each item
- White card background (`bg-white dark:bg-neutral-800`), rounded, border
- Bold text, chevron icon that rotates on expand
- Click toggles `open`

### Level 2 — Subtópico

- Nested inside level 1's expanded content
- Indented `pl-6`, same expand/collapse pattern
- Slightly smaller text, semi-bold

### Level 3 — Detalhe

- Nested inside level 2's expanded content
- Indented `pl-12`, normal weight text
- If `has_content: true`: rendered as a clickable link (brand color `text-brand`, cursor-pointer), triggers HTMX call to load modal content
- If `has_content: false`: plain text, no interaction

## Modal

### Trigger

Level 3 items with `has_content: true` have:
```html
hx-get="/htmx/details/{detail_id}"
hx-target="#detail-modal-content"
```

Clicking loads the partial into a container and Alpine opens the modal overlay.

### Layout

Fullscreen overlay with backdrop blur/dim. Centered panel, `max-w-2xl`, rounded:

- **Close button:** X icon, top-right corner
- **Video (optional):** YouTube iframe embed, `aspect-video` (16:9). Only rendered if `youtube_url` is provided.
- **Text (optional):** Markdown converted to HTML by the backend. Rendered inside a scrollable container with prose styling. Only rendered if `content_html` is provided.
- **Close methods:** Click X, click backdrop, press Escape

### Partial template: `partials/detail_modal.html`

Receives `detail` dict with optional `youtube_url` and `content_html`. Uses `{% if %}` to conditionally render each section.

## Routes

### Page route

```
GET /projects/{project_id}/collections/{collection_id}
```

- Looks up project in `MOCK_PROJECTS`, 404 if not found
- Looks up collection in `MOCK_COLLECTIONS[project_id]`, 404 if not found
- Context: `user`, `project`, `collection`, `topics` from `MOCK_TOPICS[collection_id]`
- Returns `TemplateResponse("topics.html", ...)`

### HTMX route

```
GET /htmx/details/{detail_id}
```

- Looks up detail in `MOCK_DETAILS`, 404 if not found
- Converts `content_md` to HTML via Python `markdown` library
- Context: `detail` with `youtube_url` (optional str), `content_html` (optional str), `name` (str)
- Returns `TemplateResponse("partials/detail_modal.html", ...)`

## Mock Data

### MOCK_TOPICS

Dict keyed by `collection_id`. Each collection has 3-4 topics, each topic has 2-3 subtopics, each subtopic has 2-4 details. Mix of `has_content: True` and `False`.

```python
MOCK_TOPICS = {
    collection_id: [
        {
            "id": 1,
            "name": "Tópico 1",
            "subtopics": [
                {
                    "id": 11,
                    "name": "Subtópico 1.1",
                    "details": [
                        {"id": 111, "name": "Detalhe 1.1.1", "has_content": True},
                        {"id": 112, "name": "Detalhe 1.1.2", "has_content": False},
                    ]
                }
            ]
        }
    ]
}
```

### MOCK_DETAILS

Dict keyed by `detail_id`. Some entries have both video and text, some only video, some only text.

```python
MOCK_DETAILS = {
    111: {
        "name": "Detalhe 1.1.1",
        "youtube_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "content_md": "## Resumo\n\nTexto em **markdown** aqui.",
    },
    # ...
}
```

## Navigation

- Collection cards in `collections.html` link to `/projects/{pid}/collections/{cid}`
- Header title: project name links back to `/projects/{pid}` (breadcrumb)
- Logo links to `/`

## Dependencies

- Python `markdown` library — add to project dependencies for converting markdown to HTML

## Verification

1. `make dev` — server starts on :8000
2. Navigate Home → Project → Collection → Topics screen loads
3. Header shows "Projeto / Coleção" centered, project name is a link back
4. Accordion expands/collapses at all 3 levels
5. Level 3 items with content show as clickable links
6. Clicking a link opens modal with video and/or text
7. Modal closes via X, backdrop click, or Escape
8. Items without content are plain text, not clickable
9. Dark mode works on all new elements
10. `/projects/1/collections/999` returns 404
