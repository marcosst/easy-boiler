# Library List View Toggle

## Summary

Add a grid/list view toggle to the library drawer, allowing users to switch between the current card layout and a compact list layout with smaller thumbnails. Also expand the drawer to match the chat drawer width.

## Approach

Alpine.js + localStorage. Zero backend changes. The view mode state lives in Alpine and persists via localStorage.

## Changes

### 1. Drawer width (`topics.html`)

- Expand library drawer from `w-80` (320px) to `w-[28rem]` (448px) to match the chat drawer
- Update `main` margin from `mr-80` to `mr-[28rem]` when `drawerOpen` is true

### 2. Alpine state (`topics.html`)

Add to existing `x-data`:

- `viewMode: localStorage.getItem('libraryViewMode') || 'grid'`
- `$watch('viewMode', v => localStorage.setItem('libraryViewMode', v))`

### 3. Toggle button (`topics.html`)

Single `btn_icon` placed next to the close (X) button in the drawer header. On click, toggles `viewMode` between `'grid'` and `'list'`. Icon changes dynamically:

- Grid icon (▦) when `viewMode === 'grid'`
- List icon (☰) when `viewMode === 'list'`

### 4. Item layouts (`library_item.html`)

Both layouts coexist in the same template, controlled by `x-show`:

**Grid mode** (`x-show="viewMode === 'grid'"`): Current layout unchanged — `aspect-video` image card + title below + 3-dot menu overlay.

**List mode** (`x-show="viewMode === 'list'"`): Horizontal row with flex:

- Thumbnail: `w-14 h-10` (~56x40px), `rounded-md`, same image/fallback logic as grid
- Center: type icon (YouTube red filled / PDF outline) + title with `text-ellipsis overflow-hidden`
- Right: 3-dot menu (same dropdown)
- Row styling: `bg-slate-50 dark:bg-neutral-800/50`, border, `rounded-lg`, padding
- Container spacing: the `#library-items-list` div uses `:class` to switch between `space-y-4` (grid) and `space-y-2` (list)

### 5. HTMX compatibility

New items inserted via HTMX into `#library-items-list` automatically render both layouts. The active `viewMode` determines which is visible — no extra logic needed.

## Files modified

| File | Change |
|------|--------|
| `app/templates/topics.html` | Drawer width, main margin, `viewMode` state, toggle button |
| `app/templates/partials/library_item.html` | Add list layout with `x-show`, keep grid layout |

## Files NOT modified

No changes to: backend routes, database, migrations, CSS files, other templates.
