# Library List View Toggle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a grid/list view toggle to the library drawer so users can switch between the current card layout and a compact list layout.

**Architecture:** Alpine.js manages a `viewMode` state variable persisted to localStorage. Both layouts live in the same `library_item.html` template, toggled via `x-show`. The drawer is widened to match the chat drawer (28rem).

**Tech Stack:** Alpine.js, Tailwind CSS, Jinja2

---

### Task 1: Expand drawer width and update main margin

**Files:**
- Modify: `app/templates/topics.html:94` (drawer class)
- Modify: `app/templates/topics.html:123` (main class)

- [ ] **Step 1: Update drawer width**

In `app/templates/topics.html`, line 94, change the drawer class from `w-80` to `w-[28rem]`:

```html
    class="fixed top-[72px] right-0 z-30 h-[calc(100vh-72px)] w-[28rem] bg-slate-100 dark:bg-neutral-900 border-l border-slate-200 dark:border-neutral-700 shadow-2xl overflow-y-auto dark-scrollbar"
```

- [ ] **Step 2: Update main margin when drawer is open**

In `app/templates/topics.html`, line 123, change `'mr-80': drawerOpen` to `'mr-[28rem]': drawerOpen`:

```html
  <main class="max-w-7xl mx-auto px-6 py-6" :class="{ 'mr-[28rem]': drawerOpen, 'mr-[28rem]': chatOpen }" style="transition: margin 0.3s ease;">
```

- [ ] **Step 3: Verify in browser**

Run: `make dev`

Open the topics page and toggle the library drawer. Confirm it is now the same width as the chat drawer (28rem / 448px).

- [ ] **Step 4: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: expand library drawer to match chat drawer width"
```

---

### Task 2: Add viewMode Alpine state with localStorage persistence

**Files:**
- Modify: `app/templates/topics.html:17` (x-data)

- [ ] **Step 1: Add viewMode to x-data**

In `app/templates/topics.html`, line 17, update the `x-data` to include `viewMode` with localStorage persistence:

```html
<div x-data="{ drawerOpen: false, chatOpen: false, viewMode: localStorage.getItem('libraryViewMode') || 'grid', chatMessages: [{ role: 'assistant', text: 'Olá! Sou seu assistente de estudos. Pergunte qualquer coisa sobre este assunto.' }], chatInput: '' }" x-effect="localStorage.setItem('libraryViewMode', viewMode)">
```

This adds:
- `viewMode: localStorage.getItem('libraryViewMode') || 'grid'` — reads saved preference, defaults to grid
- `x-effect="localStorage.setItem('libraryViewMode', viewMode)"` — persists on change

- [ ] **Step 2: Verify in browser console**

Open browser DevTools console. Toggle viewMode manually:

```js
document.querySelector('[x-data]').__x.$data.viewMode = 'list'
```

Check `localStorage.getItem('libraryViewMode')` returns `'list'`. Reload page, check the Alpine data still has `viewMode: 'list'`.

- [ ] **Step 3: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: add viewMode Alpine state with localStorage persistence"
```

---

### Task 3: Add toggle button to drawer header

**Files:**
- Modify: `app/templates/topics.html:107-111` (drawer header, next to close button)

- [ ] **Step 1: Add toggle button before the close button**

In `app/templates/topics.html`, replace the close button block (lines 107-111) with the toggle button followed by the close button:

```html
        <div class="flex items-center gap-1">
          <button
            @click="viewMode = viewMode === 'grid' ? 'list' : 'grid'"
            class="{{ BTN_WH }} flex items-center justify-center rounded-full bg-white dark:bg-neutral-700 hover:bg-slate-100 dark:hover:bg-neutral-600 border border-slate-400/50 dark:border-neutral-600/50 text-slate-500 dark:text-neutral-400 transition-colors cursor-pointer"
            title="Alternar visualização"
          >
            <svg x-show="viewMode === 'grid'" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"/>
            </svg>
            <svg x-show="viewMode === 'list'" x-cloak class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
              <rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
          </button>
          {{ btn_icon(
            icon='<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>',
            click='drawerOpen = false',
            title='Fechar biblioteca'
          ) }}
        </div>
```

Note: The toggle icon shows the *other* mode (list icon when in grid mode = "click to switch to list", grid icon when in list mode = "click to switch to grid").

- [ ] **Step 2: Verify in browser**

Reload the page, open the library drawer. The toggle button should appear next to the close button. Clicking it should switch the icon. Check that localStorage updates.

- [ ] **Step 3: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: add grid/list toggle button to library drawer header"
```

---

### Task 4: Add conditional spacing to items container

**Files:**
- Modify: `app/templates/topics.html:114` (library-items-list div)

- [ ] **Step 1: Make spacing conditional on viewMode**

In `app/templates/topics.html`, line 114, replace the static `space-y-4` with a dynamic class:

```html
      <div id="library-items-list" :class="viewMode === 'grid' ? 'space-y-4' : 'space-y-2'">
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/topics.html
git commit -m "feat: conditional spacing for grid vs list view mode"
```

---

### Task 5: Add list layout to library_item.html

**Files:**
- Modify: `app/templates/partials/library_item.html` (add list view, wrap grid view)

- [ ] **Step 1: Wrap existing grid layout with x-show and add list layout**

Replace the entire contents of `app/templates/partials/library_item.html` with:

```html
{% from "macros/buttons.html" import btn_icon %}
<div x-data="{ menu: false }" class="group">
  <!-- Grid view -->
  <div x-show="viewMode === 'grid'">
    <div class="relative aspect-video rounded-lg overflow-hidden bg-slate-100 dark:bg-neutral-800 border border-slate-200 dark:border-neutral-700 cursor-pointer" @click="$dispatch('open-library-modal', { type: '{{ item.type }}', url: '{{ item.url or '' }}', filePath: '{{ item.file_path or '' }}', name: '{{ item.name | e }}' })">
      <div class="w-full h-full">
        {% if item.thumbnail_url %}
        <img src="{{ item.thumbnail_url }}" alt="{{ item.name }}" class="w-full h-full object-cover">
        {% elif item.image_path %}
        <img src="/midias/{{ item.image_path }}" alt="{{ item.name }}" class="w-full h-full object-cover">
        {% else %}
        <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-teal-200 to-purple-300 dark:from-teal-900 dark:to-purple-950">
          {% if item.type == 'youtube' %}
          <svg class="w-10 h-10 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          {% else %}
          <svg class="w-10 h-10 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          {% endif %}
        </div>
        {% endif %}
      </div>
      <!-- 3-dot menu -->
      <div class="absolute top-1.5 right-1.5">
        {{ btn_icon(
          icon='<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z"/></svg>',
          click='menu = !menu',
          bg='bg-white/50 hover:bg-white/70 dark:bg-black/40 dark:hover:bg-black/60',
          text_color='text-slate-700 dark:text-white',
          extra_class='backdrop-blur-sm'
        ) }}
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
          <button @click="menu = false" class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
            <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Recarregar
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
    <p @click="$dispatch('open-library-modal', { type: '{{ item.type }}', url: '{{ item.url or '' }}', filePath: '{{ item.file_path or '' }}', name: '{{ item.name | e }}' })" class="mt-1.5 text-sm font-medium text-slate-700 dark:text-neutral-300 group-hover:text-[#26a69a] dark:group-hover:text-teal-400 transition-colors cursor-pointer">{{ item.name }}</p>
  </div>

  <!-- List view -->
  <div x-show="viewMode === 'list'" x-cloak class="relative">
    <div
      @click="$dispatch('open-library-modal', { type: '{{ item.type }}', url: '{{ item.url or '' }}', filePath: '{{ item.file_path or '' }}', name: '{{ item.name | e }}' })"
      class="flex items-center gap-3 p-2 rounded-lg bg-slate-50 dark:bg-neutral-800/50 border border-slate-200 dark:border-neutral-700 cursor-pointer hover:bg-slate-100 dark:hover:bg-neutral-700 transition-colors"
    >
      <!-- Thumbnail -->
      <div class="w-14 h-10 flex-shrink-0 rounded-md overflow-hidden bg-slate-100 dark:bg-neutral-800">
        {% if item.thumbnail_url %}
        <img src="{{ item.thumbnail_url }}" alt="{{ item.name }}" class="w-full h-full object-cover">
        {% elif item.image_path %}
        <img src="/midias/{{ item.image_path }}" alt="{{ item.name }}" class="w-full h-full object-cover">
        {% else %}
        <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-teal-200 to-purple-300 dark:from-teal-900 dark:to-purple-950">
          {% if item.type == 'youtube' %}
          <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          {% else %}
          <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          {% endif %}
        </div>
        {% endif %}
      </div>
      <!-- Type icon + title -->
      <div class="flex items-center gap-2 min-w-0 flex-1">
        {% if item.type == 'youtube' %}
        <svg class="w-4 h-4 flex-shrink-0 text-red-500" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0C.488 3.45.029 5.804 0 12c.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0C23.512 20.55 23.971 18.196 24 12c-.029-6.185-.484-8.549-4.385-8.816zM9 16V8l8 4-8 4z"/>
        </svg>
        {% else %}
        <svg class="w-4 h-4 flex-shrink-0 text-red-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        {% endif %}
        <span class="text-sm font-medium text-slate-700 dark:text-neutral-300 truncate group-hover:text-[#26a69a] dark:group-hover:text-teal-400 transition-colors">{{ item.name }}</span>
      </div>
      <!-- 3-dot menu -->
      <div class="flex-shrink-0" @click.stop>
        {{ btn_icon(
          icon='<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z"/></svg>',
          click='menu = !menu',
          extra_class='opacity-0 group-hover:opacity-100 transition-opacity'
        ) }}
      </div>
    </div>
    <!-- Dropdown menu (shared with grid) -->
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
      class="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-neutral-800 rounded-lg border border-slate-200 dark:border-neutral-700 shadow-lg overflow-hidden z-10"
    >
      <button @click="menu = false" class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
        <svg class="w-4 h-4 text-slate-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Recarregar
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
```

- [ ] **Step 2: Verify in browser**

Open the topics page, toggle between grid and list mode. Verify:
- Grid mode looks identical to before
- List mode shows small thumbnail (56x40), type icon (YouTube filled red / PDF outline red), title with ellipsis
- 3-dot menu appears on hover in list mode, opens dropdown
- Clicking an item in list mode opens the library modal
- Adding a new item via HTMX renders correctly in both modes

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/library_item.html
git commit -m "feat: add list view layout to library items"
```
