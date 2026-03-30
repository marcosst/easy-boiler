# Drawer Grabber Resize

## Summary

Add a draggable grabber (resize handle) on the left border of all drawers, allowing users to adjust drawer width by dragging. The width is shared between all drawers and persisted in localStorage. Double-click resets to the default width.

## Approach

Alpine.js pure — mousedown/mousemove/mouseup listeners on a thin div at the drawer's left edge. A single `drawerWidth` variable controls all drawers.

## Changes

### 1. Alpine state (`topics.html`)

Add to existing `x-data`:

- `drawerWidth: parseInt(localStorage.getItem('drawerWidth')) || 448` — shared width for all drawers (448px = 28rem default)
- `dragging: false` — whether a drag is in progress

Add `x-effect` to persist: `localStorage.setItem('drawerWidth', drawerWidth)`

### 2. Drawer widths (`topics.html`)

Both drawers (library and chat) replace `w-[28rem]` with dynamic inline style:

```
:style="'width:' + drawerWidth + 'px'"
```

The `main` element replaces `:class="{ 'mr-[28rem]': drawerOpen, 'mr-[28rem]': chatOpen }"` with:

```
:style="(drawerOpen || chatOpen) ? 'margin-right:' + drawerWidth + 'px; transition: margin 0.3s ease' : 'transition: margin 0.3s ease'"
```

### 3. Grabber element

A `div` added as the first child inside each drawer:

- Position: `absolute left-0 top-0 h-full w-1`
- Cursor: `cursor-col-resize`
- z-index: `z-10` (above drawer content)
- Hover: expands to `w-2`, shows `bg-slate-300/50 dark:bg-neutral-600/50`
- Active/dragging: same visible style as hover

Events on the grabber:
- `@mousedown.prevent="dragging = true"` — starts drag
- `@dblclick="drawerWidth = 448"` — resets to default

### 4. Drag listeners

On the main `x-data` container div:
- `@mousemove.window="if (dragging) drawerWidth = Math.min(Math.max(window.innerWidth - $event.clientX, 200), window.innerWidth * 0.5)"` — calculates width from cursor position, clamped between 200px and 50% of viewport
- `@mouseup.window="dragging = false"` — ends drag

### 5. Drag UX

On the main `x-data` container div, add `:class="{ 'select-none': dragging }"` to prevent text selection during drag.

### 6. Limits

- Minimum width: 200px
- Maximum width: 50% of `window.innerWidth`
- Default: 448px (28rem)

## Files modified

| File | Change |
|------|--------|
| `app/templates/topics.html` | `drawerWidth`/`dragging` state, `x-effect` persistence, dynamic widths on both drawers and main, grabber elements, drag listeners, select-none during drag |

## Files NOT modified

No changes to: backend routes, database, migrations, CSS files, other templates, `library_item.html`.
