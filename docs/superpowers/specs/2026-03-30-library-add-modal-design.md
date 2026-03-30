# Library Items — Add Modal & Type Constraint

## Objetivo

Restringir tipos de `library_items` para `youtube` e `pdf`, e implementar modal para adicionar itens à biblioteca com preview automático (thumbnail + título/nome).

## 1. Database Migration

Nova migration dbmate que recria `library_items` com constraint atualizada:

```sql
CHECK(type IN ('youtube', 'pdf'))
```

Dados existentes com `type = 'video'` migrados para `'youtube'`. Mesma técnica de recriação de tabela usada na migration `content_json`.

## 2. Armazenamento de Arquivos

```
midias/
  {username}/
    thumbnails/
      {uuid}.jpg          ← thumbnails (youtube e pdf)
    pdfs/
      {uuid}.pdf          ← arquivos pdf uploadados
```

- Nomes com UUID para evitar colisão
- `image_path` no DB: caminho relativo a `midias/` (ex: `marocssr/thumbnails/abc123.jpg`)
- PDFs: `file_path` = caminho relativo (ex: `marocssr/pdfs/def456.pdf`), `url` = NULL
- YouTube: `url` = URL original, `file_path` = NULL

## 3. Dependências Novas

- `pymupdf` — geração de thumbnail da primeira página do PDF (pure Python, sem dependência de sistema)
- `httpx` — mover de dev para dependência principal (usado para oEmbed e download de thumbnails do YouTube)

## 4. Backend — Novos Endpoints

### `POST /htmx/library/preview`

Recebe tipo + conteúdo, retorna fragment HTML com preview.

**YouTube:**
1. Extrai video ID com regex existente (`YOUTUBE_RE`)
2. Busca título via oEmbed (`https://noembed.com/embed?url=...`) com `httpx`
3. Baixa thumbnail de `img.youtube.com/vi/{id}/mqdefault.jpg`
4. Salva thumbnail em `midias/{username}/thumbnails/{uuid}.jpg`
5. Retorna fragment HTML: thumbnail + campo nome pré-preenchido com título do vídeo (editável)

**PDF:**
1. Salva PDF em `midias/{username}/pdfs/{uuid}.pdf`
2. Gera thumbnail da primeira página com `pymupdf` (600px largura)
3. Salva thumbnail em `midias/{username}/thumbnails/{uuid}.jpg`
4. Retorna fragment HTML: thumbnail + campo nome pré-preenchido com nome do arquivo sem extensão (editável)

**Erro:** Retorna fragment com mensagem de erro (URL inválida, oEmbed timeout, PDF corrompido).

### `POST /htmx/library/save`

Recebe: `subject_id`, `type`, `name`, `url` (youtube), `file_path` (pdf), `image_path`.

1. Insere em `library_items` com `position` = MAX(position) + 1 para o subject
2. Retorna fragment HTML com o novo item renderizado para inserção via HTMX no drawer da biblioteca

## 5. Frontend — Modal de Adicionar

O modal abre ao clicar no botão "+" existente no drawer da biblioteca (`topics.html` linha 99).

### Estado 1: Seleção de Tipo

Dois cards grandes lado a lado:
- **YouTube** — ícone ▶ + label "YouTube", fundo teal quando selecionado
- **PDF** — ícone 📄 + label "PDF", fundo teal quando selecionado

Ao clicar num card, o outro fica opaco/desabilitado e o campo de input aparece abaixo.

### Estado 2: Input + Loading

**YouTube selecionado:**
- Campo de texto para URL
- Botão "Buscar vídeo"
- Ao clicar "Buscar": HTMX POST para `/htmx/library/preview` com `type=youtube&url=...`
- Spinner no botão durante a requisição

**PDF selecionado:**
- Botão de upload de arquivo (accept=".pdf")
- Ao selecionar arquivo: HTMX POST para `/htmx/library/preview` com multipart form (type=pdf + file)
- Spinner durante upload + geração de thumbnail

### Estado 3: Preview + Confirmação

Fragment HTML retornado pelo `/htmx/library/preview` substitui a área de input:
- Indicador de sucesso na URL/arquivo (✓ verde)
- Thumbnail (aspect-ratio 16:9)
- Campo "Nome" editável (pré-preenchido com título do vídeo ou nome do arquivo)
- Botão "Salvar na biblioteca" — desabilitado durante loading, habilitado após preview carregar
- Ao salvar: HTMX POST para `/htmx/library/save`

### Após Salvar

- Modal fecha
- Novo item aparece no drawer da biblioteca (HTMX swap)

## 6. Template Partials Novos

- `partials/library_add_modal.html` — modal completo com Alpine.js state
- `partials/library_preview.html` — fragment retornado pelo endpoint preview (thumbnail + nome editável + botão salvar)
- `partials/library_item.html` — fragment de um item da biblioteca (reutilizável no drawer)

## 7. Fluxo HTMX

```
[Botão "+"] → abre modal (Alpine.js)
  ↓
[Seleciona tipo] → mostra input (Alpine.js)
  ↓
[Cola URL / Upload PDF] → POST /htmx/library/preview
  ↓
[Preview retornado] → hx-target substitui área de input
  ↓
[Edita nome + Salvar] → POST /htmx/library/save
  ↓
[Item retornado] → hx-target insere no drawer + fecha modal
```
