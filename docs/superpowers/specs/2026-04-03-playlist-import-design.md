# Playlist Import — Design Spec

## Objetivo

Permitir que o usuário importe múltiplos vídeos de uma playlist do YouTube de uma só vez na tela de inclusão na biblioteca.

## Comportamento

### Fluxo por tipo de URL

| URL | Comportamento |
|-----|---------------|
| `youtube.com/watch?v=abc` (sem playlist) | Preview normal, sem alteração |
| `youtube.com/watch?v=abc&list=XYZ` | Preview normal do vídeo + checkbox "Incluir vídeos da playlist" desmarcado |
| `youtube.com/playlist?list=XYZ` (sem v=) | Vai direto para lista de vídeos da playlist |

### Estado 1 — Preview com checkbox (URL com v= + list=)

- Thumbnail do vídeo específico (comportamento atual)
- Campo nome editável (comportamento atual)
- **Novo:** Checkbox "Incluir vídeos da playlist" — desmarcado por padrão
- Botão "Salvar na biblioteca" salva apenas o vídeo individual (comportamento atual)

### Estado 2 — Lista de vídeos (após marcar checkbox ou URL só com list=)

- Checkbox master "Incluir vídeos da playlist" no topo (marcado)
- Contador "X de Y selecionados" ao lado
- Lista scrollável (max-height com overflow-y) de vídeos:
  - **Vídeos novos:** checkbox marcado por padrão + thumbnail 56px + título
  - **Vídeos já na biblioteca:** sem checkbox, thumbnail + título em cinza (opacity reduzida), label "(já na biblioteca)"
- O vídeo original (do `v=`) aparece como item normal na lista
- Desmarcar o checkbox master volta ao Estado 1 (preview individual) — só disponível quando a URL original tinha `v=`. Para URLs só com `list=`, o checkbox master não é desmarcável (a lista é o único estado possível)
- Botão "Salvar X vídeos na biblioteca" com contagem dinâmica

### Salvamento

- Todos os vídeos selecionados são salvos de uma vez (bulk insert)
- Cada um é inserido em `library_items` com `status='pending'`
- Cada um é enfileirado no worker para processamento (Apify subtitles + LLM)
- Modal fecha após salvar, itens aparecem na biblioteca

## Backend

### Alteração: `POST /htmx/library/preview`

Na rota existente (`app/main.py:645`), após extrair o video_id:

1. Verificar se a URL contém parâmetro `list=`
2. Se tem `list=` + `v=`: retornar o preview normal com flag `is_playlist=True` no template context
3. Se tem só `list=` (sem `v=`): chamar a lógica de listar vídeos da playlist e retornar o partial `library_playlist_videos.html` diretamente

Regex de playlist: extrair `list` de `urllib.parse.parse_qs(parsed.query)`.

### Nova rota: `POST /htmx/library/playlist-videos`

- **Input:** `url` (URL da playlist), `subject_id`
- **Processo:**
  1. Chamar Apify actor `streamers/youtube-scraper` com `downloadSubtitles=false` e a URL da playlist
  2. Receber array de vídeos com `title`, `id`, `thumbnailUrl`
  3. Consultar duplicatas: `SELECT url FROM library_items WHERE subject_id = ? AND type = 'youtube' AND deleted_at IS NULL`
  4. Extrair video_ids das URLs existentes
  5. Marcar cada vídeo como `existing` ou `new`
- **Output:** Renderiza `partials/library_playlist_videos.html`

### Alteração: `POST /htmx/library/save`

Aceitar múltiplos vídeos via campos de formulário repetidos:
- `urls[]` — lista de URLs dos vídeos selecionados
- `names[]` — lista de nomes correspondentes
- `image_paths[]` — lista de thumbnails

Para cada vídeo: inserir em `library_items`, baixar thumbnail, enfileirar no worker. Retornar HTML de todos os novos itens concatenados.

### Chamada Apify

Reutilizar a infraestrutura existente. Input do actor:
```json
{
  "startUrls": [{"url": "https://youtube.com/playlist?list=XYZ"}],
  "downloadSubtitles": false,
  "maxResults": 200
}
```

Criar função `fetch_playlist_videos(url: str) -> list[dict]` em `app/main.py` (ou módulo auxiliar) que retorna lista de `{"video_id": str, "title": str, "thumbnail_url": str}`.

### Timeout e erros

- Skeleton loader no frontend durante a chamada Apify
- Se falhar: mensagem de erro no lugar da lista, com botão "Tentar novamente"
- Timeout da chamada Apify: usar o mesmo `APIFY_YOUTUBE_TIMEOUT_SECS` do `.env`

## Frontend

### Alteração: `partials/library_preview.html`

Quando `is_playlist` é True:
- Adicionar checkbox "Incluir vídeos da playlist" abaixo da thumbnail
- Checkbox com `hx-post="/htmx/library/playlist-videos"` e `hx-target="#playlist-videos-area"`
- Div `#playlist-videos-area` como target para a lista de vídeos

### Novo partial: `partials/library_playlist_videos.html`

Lista de vídeos da playlist com:
- Checkbox master no topo (marcado, com contador)
- Lista scrollável de itens
- Cada item novo: `<input type="checkbox" name="urls[]" value="{url}" checked>` + thumbnail + título
- Cada item existente: sem input, estilo cinza
- Hidden inputs para `subject_id` e `type`
- Botão submit com contagem dinâmica via Alpine.js
- Skeleton loader para estado de carregamento

### Alpine.js — estado do modal

Adicionar ao `x-data` do modal (`library_add_modal.html`):
- `playlistMode: false` — controla se está mostrando lista de playlist
- Marcar checkbox: `playlistMode = true`, dispara HTMX
- Desmarcar checkbox: `playlistMode = false`, restaura preview original

## Arquivos impactados

| Arquivo | Tipo de mudança |
|---------|----------------|
| `app/main.py` | Alterar preview route, alterar save route, nova route playlist-videos |
| `app/templates/partials/library_preview.html` | Adicionar checkbox e target div |
| `app/templates/partials/library_playlist_videos.html` | **Novo** — lista de vídeos |
| `app/templates/partials/library_add_modal.html` | Adicionar `playlistMode` ao x-data |

## Fora de escopo

- Migração de banco (não precisa de novos campos)
- Alteração no worker (processamento individual continua igual)
- Suporte a playlists para PDFs
