# UI Consistency Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate visual inconsistencies across all templates — inputs, buttons, modals, and layout — so the UI feels like one cohesive design system.

**Architecture:** Define standard Tailwind class strings as Jinja2 globals (same pattern as existing `BTN_H`/`BTN_WH`), then update every template to reference those globals. No new files — only edits to `app/main.py` and existing templates.

**Tech Stack:** Jinja2 globals, Tailwind CSS classes, existing macro system in `macros/buttons.html`.

---

## File Map

- **Modify:** `app/main.py:60-64` — add new class-string globals (`INPUT_CLS`, `INPUT_CLS_ERR`, `BTN_PRIMARY`)
- **Modify:** `app/templates/login.html` — use `INPUT_CLS` and `BTN_PRIMARY`
- **Modify:** `app/templates/register.html` — use `INPUT_CLS` and `BTN_PRIMARY`
- **Modify:** `app/templates/choose_username.html` — fix logo alignment, use `INPUT_CLS` and `BTN_PRIMARY`
- **Modify:** `app/templates/landing.html` — reuse `partials/header.html`, keep search input as bespoke hero variant
- **Modify:** `app/templates/home.html` — use `INPUT_CLS` in subject modal, standardize modal container
- **Modify:** `app/templates/topics.html` — standardize media modal and delete modal containers
- **Modify:** `app/templates/partials/library_add_modal.html` — use `INPUT_CLS`, standardize modal container and buttons
- **Modify:** `app/templates/partials/library_preview.html` — use `INPUT_CLS` and `BTN_PRIMARY`
- **Modify:** `app/templates/partials/library_playlist_videos.html` — use `BTN_PRIMARY`

---

## Canonical Values (reference for all tasks)

These are the **standardized values** every task below should converge on:

| Token | Classes |
|-------|---------|
| `INPUT_CLS` | `w-full px-3.5 py-2.5 bg-white dark:bg-neutral-800 border border-slate-200 dark:border-neutral-700 rounded-lg text-slate-700 dark:text-neutral-300 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-colors` |
| `INPUT_CLS_ERR` | `w-full px-3.5 py-2.5 bg-white dark:bg-neutral-800 border border-red-400 dark:border-red-500 rounded-lg text-slate-700 dark:text-neutral-300 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500 transition-colors` |
| `BTN_PRIMARY` | `w-full h-10 rounded-lg bg-brand hover:bg-brand-dark text-white text-sm font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed` |
| Modal form container | `max-w-md` width, `bg-white dark:bg-neutral-800` background |
| Modal content viewer | `max-w-4xl` width (video/PDF embed) |
| Modal confirm/delete | `max-w-sm` width |
| Label | `block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5` |

---

### Task 1: Add global class-string tokens in `app/main.py`

**Files:**
- Modify: `app/main.py:60-64`

- [ ] **Step 1: Add the new globals after the existing BTN_H/BTN_WH block**

Replace lines 60-64 of `app/main.py`:

```python
# Global button size tokens — change here to resize all buttons
BTN_H = "h-10"
BTN_WH = "w-10 h-10"
templates.env.globals["BTN_H"] = BTN_H
templates.env.globals["BTN_WH"] = BTN_WH
```

With:

```python
# Global UI tokens — change here to update all components consistently
BTN_H = "h-10"
BTN_WH = "w-10 h-10"
INPUT_CLS = (
    "w-full px-3.5 py-2.5 bg-white dark:bg-neutral-800 border border-slate-200"
    " dark:border-neutral-700 rounded-lg text-slate-700 dark:text-neutral-300 text-sm"
    " placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2"
    " focus:ring-teal-500/50 focus:border-teal-500 transition-colors"
)
INPUT_CLS_ERR = (
    "w-full px-3.5 py-2.5 bg-white dark:bg-neutral-800 border border-red-400"
    " dark:border-red-500 rounded-lg text-slate-700 dark:text-neutral-300 text-sm"
    " placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2"
    " focus:ring-red-500/50 focus:border-red-500 transition-colors"
)
BTN_PRIMARY = (
    "w-full h-10 rounded-lg bg-brand hover:bg-brand-dark text-white text-sm"
    " font-semibold transition-colors cursor-pointer disabled:opacity-50"
    " disabled:cursor-not-allowed"
)
LABEL_CLS = (
    "block text-xs font-semibold text-slate-500 dark:text-neutral-400"
    " uppercase tracking-wider mb-1.5"
)
templates.env.globals["BTN_H"] = BTN_H
templates.env.globals["BTN_WH"] = BTN_WH
templates.env.globals["INPUT_CLS"] = INPUT_CLS
templates.env.globals["INPUT_CLS_ERR"] = INPUT_CLS_ERR
templates.env.globals["BTN_PRIMARY"] = BTN_PRIMARY
templates.env.globals["LABEL_CLS"] = LABEL_CLS
```

- [ ] **Step 2: Verify the app still starts**

Run: `cd /home/ubuntu/aaaa/easy-boiler && make dev`
Expected: uvicorn starts without import errors.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add INPUT_CLS, BTN_PRIMARY, LABEL_CLS global UI tokens"
```

---

### Task 2: Standardize `login.html`

**Files:**
- Modify: `app/templates/login.html`

- [ ] **Step 1: Replace input classes with `{{ INPUT_CLS }}`**

In `login.html`, the two `<input>` elements (email, password) currently use:
```
class="w-full px-3.5 py-2.5 bg-white dark:bg-neutral-800 border border-slate-300 dark:border-neutral-700 rounded-lg text-slate-700 dark:text-neutral-300 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors"
```

Replace **both** with:
```
class="{{ INPUT_CLS }}"
```

- [ ] **Step 2: Replace button classes with `{{ BTN_PRIMARY }}`**

The submit button currently uses:
```
class="w-full py-2.5 bg-brand hover:bg-brand-dark text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer"
```

Replace with:
```
class="{{ BTN_PRIMARY }}"
```

- [ ] **Step 3: Verify login page renders correctly**

Open `http://localhost:8000/login` in the browser. Verify:
- Inputs have visible border, teal focus ring
- Button is full-width, teal/brand colored, `h-10`
- Dark mode toggle works (check both modes)

- [ ] **Step 4: Commit**

```bash
git add app/templates/login.html
git commit -m "refactor: use global UI tokens in login.html"
```

---

### Task 3: Standardize `register.html`

**Files:**
- Modify: `app/templates/register.html`

- [ ] **Step 1: Replace input classes with `{{ INPUT_CLS }}`**

In `register.html`, there are 4 `<input>` elements: username, email, password, password_confirm.

All four currently use the same long class string (same as login). Replace each with:
```
class="{{ INPUT_CLS }}"
```

- [ ] **Step 2: Replace button classes with `{{ BTN_PRIMARY }}`**

The "Criar conta" submit button currently uses:
```
class="w-full py-2.5 bg-brand hover:bg-brand-dark text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer"
```

Replace with:
```
class="{{ BTN_PRIMARY }}"
```

- [ ] **Step 3: Verify register page renders correctly**

Open `http://localhost:8000/register`. Verify inputs, password strength bar, and button look correct in both themes.

- [ ] **Step 4: Commit**

```bash
git add app/templates/register.html
git commit -m "refactor: use global UI tokens in register.html"
```

---

### Task 4: Fix and standardize `choose_username.html`

**Files:**
- Modify: `app/templates/choose_username.html`

- [ ] **Step 1: Fix logo alignment — change `justify-between` to `justify-center`**

Line 6 currently:
```html
<div class="flex items-center justify-between mb-8">
```

Replace with:
```html
<div class="flex justify-center mb-8">
```

Also wrap the img in an `<a>` tag like login/register do:
```html
<div class="flex justify-center mb-8">
  <a href="/login">
    <img src="/static/resumiu-header.svg" alt="resumiu" class="h-14">
  </a>
</div>
```

- [ ] **Step 2: Replace input class with `{{ INPUT_CLS }}`**

The username input currently uses the same long class string. Replace with:
```
class="{{ INPUT_CLS }}"
```

- [ ] **Step 3: Replace button class with `{{ BTN_PRIMARY }}`**

The "Continuar" button currently uses:
```
class="w-full py-2.5 bg-brand hover:bg-brand-dark text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer"
```

Replace with:
```
class="{{ BTN_PRIMARY }}"
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/choose_username.html
git commit -m "fix: center logo on choose_username page, use global UI tokens"
```

---

### Task 5: Standardize `home.html` subject modal

**Files:**
- Modify: `app/templates/home.html`

- [ ] **Step 1: Standardize modal container**

Line 278, change the modal dialog classes from:
```
class="mx-auto flex w-full max-w-[460px] flex-col overflow-hidden rounded-2xl bg-slate-100 shadow-2xl will-change-auto dark:bg-neutral-800 dark:text-neutral-100 max-h-[85vh] overflow-y-auto dark-scrollbar"
```

To:
```
class="mx-auto flex w-full max-w-md flex-col overflow-hidden rounded-2xl bg-white shadow-2xl will-change-auto dark:bg-neutral-800 dark:text-neutral-100 max-h-[85vh] overflow-y-auto dark-scrollbar"
```

Changes: `max-w-[460px]` → `max-w-md` (448px, standardized), `bg-slate-100` → `bg-white`.

- [ ] **Step 2: Replace input classes with globals**

The subject modal has 3 inputs: title (line 331), shortname (line 352), delete confirm (line 378).

For **title** and **shortname**, which use dynamic `:class` for error states, update the static class and the Alpine binding.

Title input — replace:
```html
class="w-full px-3.5 py-2.5 rounded-lg border text-sm bg-white dark:bg-neutral-900 text-slate-700 dark:text-neutral-300 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 transition-colors"
:class="error_field === 'name' ? 'border-red-400 dark:border-red-500' : 'border-slate-200 dark:border-neutral-700'"
```

With:
```html
:class="error_field === 'name' ? '{{ INPUT_CLS_ERR }}' : '{{ INPUT_CLS }}'"
```

Apply the same pattern to the **shortname** input (replacing its `:class` with the same error_field check for `'shortname'`).

For the **delete confirm** input, replace:
```html
class="flex-1 px-3.5 py-2.5 rounded-lg border border-red-200 dark:border-red-900/50 text-sm bg-white dark:bg-neutral-900 text-slate-700 dark:text-neutral-300 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-red-500/50"
```

With (keep `flex-1` instead of `w-full`, keep red border since this is always in danger zone):
```html
class="flex-1 px-3.5 py-2.5 bg-white dark:bg-neutral-800 border border-red-200 dark:border-red-900/50 rounded-lg text-slate-700 dark:text-neutral-300 text-sm placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-red-500/50 transition-colors"
```

(Only change: `dark:bg-neutral-900` → `dark:bg-neutral-800` for consistency.)

- [ ] **Step 3: Replace label classes with `{{ LABEL_CLS }}`**

There are 3 labels in the subject modal: "Título" (line 328), "Nome curto" (line 345), "Visibilidade" (line 360).

Each currently uses:
```
class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5"
```

Replace with:
```
class="{{ LABEL_CLS }}"
```

- [ ] **Step 4: Verify subject modal renders correctly**

Open `http://localhost:8000/<username>`, click "Novo Assunto". Verify inputs, labels, and error states look correct.

- [ ] **Step 5: Commit**

```bash
git add app/templates/home.html
git commit -m "refactor: standardize subject modal — use global UI tokens, max-w-md, bg-white"
```

---

### Task 6: Standardize `library_add_modal.html`

**Files:**
- Modify: `app/templates/partials/library_add_modal.html`

- [ ] **Step 1: Standardize modal container background**

Line 59, the modal dialog class currently includes `bg-white dark:bg-neutral-800` — this is already correct. No change needed for background.

Confirm `max-w-md` is already used (line 59: `max-w-md`). Correct, no change needed.

- [ ] **Step 2: Replace input classes**

The YouTube URL input (line 108) currently uses:
```
class="w-full rounded-lg border border-slate-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
```

Replace with:
```
class="{{ INPUT_CLS }}"
```

- [ ] **Step 3: Replace button classes with `{{ BTN_PRIMARY }}`**

The "Buscar vídeo" button (line 111-112) currently uses:
```
class="w-full h-10 rounded-lg bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-white text-sm font-semibold transition-colors cursor-pointer flex items-center justify-center"
```

Replace with:
```
class="{{ BTN_PRIMARY }} flex items-center justify-center"
```

(Keep `flex items-center justify-center` since this button has a spinner icon.)

- [ ] **Step 4: Replace label classes with `{{ LABEL_CLS }}`**

Two labels: "URL do vídeo" (line 106) and "Arquivo PDF" (line 140).

Each currently uses:
```
class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1"
```

Replace both with:
```
class="{{ LABEL_CLS }}"
```

(Note: `mb-1` becomes `mb-1.5` from the global — this is the standardization fix.)

- [ ] **Step 5: Verify library add modal renders correctly**

Navigate to a subject, open the library drawer, click "+". Verify YouTube/PDF forms look correct.

- [ ] **Step 6: Commit**

```bash
git add app/templates/partials/library_add_modal.html
git commit -m "refactor: use global UI tokens in library add modal"
```

---

### Task 7: Standardize `library_preview.html`

**Files:**
- Modify: `app/templates/partials/library_preview.html`

- [ ] **Step 1: Replace input classes**

There are two "Nome" inputs: one in the error re-render form (line 33) and one in the main preview form (line 94-95).

Both currently use:
```
class="w-full rounded-lg border border-slate-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
```

Replace both with:
```
class="{{ INPUT_CLS }}"
```

- [ ] **Step 2: Replace button classes**

Two "Salvar na biblioteca" buttons (line 37-38 and line 101-102) currently use:
```
class="w-full h-10 rounded-lg bg-teal-500 hover:bg-teal-600 text-white text-sm font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
```

Replace both with:
```
class="{{ BTN_PRIMARY }}"
```

- [ ] **Step 3: Replace label classes**

Two "Nome" labels (line 31 and line 93) currently use:
```
class="block text-xs font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider mb-1"
```

Replace both with:
```
class="{{ LABEL_CLS }}"
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/partials/library_preview.html
git commit -m "refactor: use global UI tokens in library preview"
```

---

### Task 8: Standardize `library_playlist_videos.html`

**Files:**
- Modify: `app/templates/partials/library_playlist_videos.html`

- [ ] **Step 1: Replace button class**

The "Salvar N vídeos na biblioteca" button (line 70-71) currently uses:
```
class="w-full h-10 rounded-lg bg-teal-500 hover:bg-teal-600 text-white text-sm font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
```

Replace with:
```
class="{{ BTN_PRIMARY }}"
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/partials/library_playlist_videos.html
git commit -m "refactor: use BTN_PRIMARY token in playlist videos"
```

---

### Task 9: Standardize modals in `topics.html`

**Files:**
- Modify: `app/templates/topics.html`

- [ ] **Step 1: Standardize media viewer modal background**

Line 306, the media modal dialog uses:
```
class="mx-auto flex w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-slate-100 shadow-2xl will-change-auto dark:bg-neutral-800 dark:text-neutral-100"
```

Change `bg-slate-100` to `bg-white`:
```
class="mx-auto flex w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl will-change-auto dark:bg-neutral-800 dark:text-neutral-100"
```

(This modal keeps `max-w-4xl` — it's the content viewer, deliberately wider.)

- [ ] **Step 2: Standardize chat textarea**

Line 141, the chat textarea currently uses:
```
class="flex-1 resize-none rounded-xl border border-slate-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2.5 text-sm text-slate-700 dark:text-neutral-300 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
```

This is a **bespoke variant** — it uses `rounded-xl`, `px-4`, `flex-1`, and `resize-none` for the chat context. Keep it as-is but align the focus style. Replace `focus:border-transparent` with `focus:border-teal-500`:

```
class="flex-1 resize-none rounded-xl border border-slate-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2.5 text-sm text-slate-700 dark:text-neutral-300 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500"
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/topics.html
git commit -m "refactor: standardize modal bg and focus styles in topics.html"
```

---

### Task 10: Reuse header partial in `landing.html`

**Files:**
- Modify: `app/templates/landing.html`

- [ ] **Step 1: Replace inline header with partial include**

Currently `landing.html` has its own inline header (lines 7-17) that duplicates the unauthenticated header from `partials/header.html`. The partial already handles the no-user case (lines 162-165) with identical buttons.

Replace:
```html
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
```

With:
```html
{% include "partials/header.html" %}
```

The partial's center section (`header_title_text`) will render empty when no title variables are set, which is correct — the logo and auth buttons will still be at opposite ends due to the flex layout.

- [ ] **Step 2: Verify the landing page looks the same**

Open `http://localhost:8000/` (logged out). Verify the header renders identically: logo left, Entrar/Criar conta right.

- [ ] **Step 3: Commit**

```bash
git add app/templates/landing.html
git commit -m "refactor: reuse header partial in landing page"
```

---

### Task 11: Final visual QA pass

- [ ] **Step 1: Check all pages in light mode**

Open each page in sequence and verify visually:
1. `/` (landing, logged out)
2. `/login`
3. `/register`
4. `/<username>` (home, logged in)
5. `/<username>/<subject>` (topics)
6. Open subject modal (create + edit)
7. Open library drawer → add modal → YouTube flow
8. Open library drawer → add modal → PDF flow

- [ ] **Step 2: Check all pages in dark mode**

Toggle to dark mode and repeat the same flow.

- [ ] **Step 3: Check focus rings**

Tab through inputs on login, register, and subject modal. All should show the same teal-500/50 ring.

- [ ] **Step 4: Verify no regressions — check for broken classes**

Run in the terminal:
```bash
grep -rn 'bg-neutral-900' app/templates/ --include="*.html"
```

Expected: only `landing.html` search input (hero variant) and danger-zone delete input should still reference `neutral-900`. All other inputs should now use `INPUT_CLS` (which uses `neutral-800`).

```bash
grep -rn 'focus:ring-1\|focus:ring-brand\|focus:border-brand\|focus:border-transparent' app/templates/ --include="*.html"
```

Expected: zero matches. All focus styles should now be `ring-2 ring-teal-500/50 border-teal-500`.

- [ ] **Step 5: Commit any fixes discovered during QA**

```bash
git add -A
git commit -m "fix: address issues found during visual QA pass"
```

(Only if fixes were needed.)
