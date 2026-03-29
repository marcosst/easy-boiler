# Dark Mode Toggle Design

## Context

The app currently has no dark mode support. The user dropdown in `grid_page.html` needs a "Tema" (Theme) sub-item that lets users switch between Light, Dark, and Auto modes. Auto follows the OS preference and is the default when no choice has been saved.

## Approach

Tailwind CSS `darkMode: 'class'` with Alpine.js managing the `dark` class on `<html>`. Theme preference persisted in `localStorage`.

## Tailwind Configuration

In `base.html`, configure the Tailwind CDN script with `darkMode: 'class'`:

```html
<script>
  tailwind.config = { darkMode: 'class' }
</script>
```

## Theme Manager (Alpine.js on `<html>`)

An Alpine.js `x-data` component on the `<html>` element manages the theme lifecycle:

- **On init:** reads `localStorage.getItem('theme')`.
  - `'light'` → remove `dark` class
  - `'dark'` → add `dark` class
  - `'auto'` or absent (default) → check `window.matchMedia('(prefers-color-scheme: dark)')`. If matches, add `dark`; otherwise remove. Register a `change` listener on the media query to react to OS changes in real time.
- **On switch:** `setTheme(mode)` saves to `localStorage`, updates the `dark` class, and manages the media query listener (add for auto, remove for light/dark).
- The current mode is exposed as `theme` for the dropdown to highlight the active option.

## Dropdown: "Tema" Sub-Item

Location: between "Configurações" and the separator before "Sair" in the user dropdown (`grid_page.html`).

### Structure

```
Meu Perfil
Configurações
───────────
Tema  ▾
  [ ☀ Claro ] [ 🌙 Escuro ] [ 🖥 Auto ]
───────────
Sair
```

### Behavior

- Clicking "Tema" toggles (`x-show`) an inline panel with 3 pill-style buttons side by side.
- The active mode gets a highlighted style (e.g., `bg-blue-600 text-white`); inactive modes get a muted style.
- Clicking an option calls `setTheme('light' | 'dark' | 'auto')`, updates `localStorage`, toggles the `dark` class on `<html>`, and the panel stays open for visual feedback.
- Icons: sun (light), moon (dark), monitor (auto) — inline SVGs matching the existing dropdown icon style.

## Dark Mode Color Mapping

All existing templates (`base.html`, `grid_page.html`, `home.html`, `collections.html`) gain `dark:` variant classes:

| Element | Light (current) | Dark |
|---|---|---|
| `<body>` | `bg-slate-100` | `dark:bg-slate-900` |
| Header | `bg-white border-slate-200` | `dark:bg-slate-800 dark:border-slate-700` |
| Cards (projects/collections) | `bg-white border-slate-200` | `dark:bg-slate-800 dark:border-slate-700` |
| Primary text | `text-slate-800` | `dark:text-slate-100` |
| Secondary text | `text-slate-700`, `text-slate-400` | `dark:text-slate-300`, `dark:text-slate-500` |
| Dropdown menu | `bg-white border-slate-200` | `dark:bg-slate-800 dark:border-slate-700` |
| Dropdown hover | `hover:bg-slate-50` | `dark:hover:bg-slate-700` |
| Avatar button | `bg-slate-100 hover:bg-slate-200` | `dark:bg-slate-700 dark:hover:bg-slate-600` |
| "Sair" link | `text-red-600 hover:bg-red-50` | `dark:text-red-400 dark:hover:bg-red-900/30` |
| Dropdown identity text | `text-slate-800`, `text-slate-400` | `dark:text-slate-100`, `dark:text-slate-500` |
| Dropdown border separators | `border-slate-100` | `dark:border-slate-700` |

General pattern: white backgrounds → `slate-800`, `slate-200` borders → `slate-700`, `slate-800` text → `slate-100`.

## Default Behavior

- When `localStorage` has no `theme` key, the app defaults to **Auto** (follows OS `prefers-color-scheme`).
- The "Auto" pill is highlighted in the dropdown when no explicit choice has been made.

## Files Modified

- `app/templates/base.html` — Tailwind config + Alpine theme manager on `<html>`
- `app/templates/grid_page.html` — "Tema" sub-item in dropdown + dark variant classes on header/dropdown
- `app/templates/home.html` — dark variant classes on cards
- `app/templates/collections.html` — dark variant classes on cards

## Verification

1. `make dev` — server starts on :8000
2. Open home — defaults to Auto (matches OS preference)
3. Open dropdown → click "Tema" → panel expands with 3 options, "Auto" highlighted
4. Click "Escuro" → page goes dark immediately, "Escuro" highlighted
5. Click "Claro" → page goes light, "Claro" highlighted
6. Click "Auto" → follows OS, "Auto" highlighted
7. Refresh page → theme persists from `localStorage`
8. Navigate to collections screen → dark mode applies consistently
9. Change OS preference while on Auto → page reacts in real time
