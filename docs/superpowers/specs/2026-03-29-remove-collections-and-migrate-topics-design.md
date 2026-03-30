# Design: Remover Coleções, Migrar Tópicos para Markdown, Adicionar Biblioteca

**Data:** 2026-03-29

## Resumo

Simplificar a hierarquia do app removendo a camada de coleções. Tópicos passam a ser armazenados como markdown no projeto (`content_md`), e o sistema faz parse dos headings para montar a UI. Adicionalmente, criar a tabela `library_items` como repositório de materiais fonte (vídeos, PDFs, docs) vinculados ao projeto.

## Escopo

### Incluído
- Remover todo código, templates, testes e rotas de coleções
- Adicionar campo `content_md` à tabela `projects`
- Criar tabela `library_items`
- Parser de markdown → estrutura hierárquica para accordion
- Nova rota `/{username}/{shortname}` para visualizar tópicos
- Rota HTMX para carregar conteúdo de detalhe no modal
- Reescrever testes relevantes

### Excluído (próxima fase)
- Processamento LLM (gerar tópicos a partir da biblioteca)
- CRUD de library_items (UI/rotas)
- Rota de visualização da biblioteca

---

## 1. Schema do Banco de Dados

### Tabela `projects` — campo adicionado

```sql
ALTER TABLE projects ADD COLUMN content_md TEXT;
```

O `content_md` armazena o markdown completo dos tópicos do projeto, seguindo a convenção de headings:

```markdown
# Tópico 1
## Subtópico 1.1
### Detalhe 1.1.1
Conteúdo markdown do detalhe, com texto, links de vídeo, etc.
### Detalhe 1.1.2
Mais conteúdo...
## Subtópico 1.2
### Detalhe 1.2.1
...
```

- `#` = nível 1 (tópico)
- `##` = nível 2 (subtópico)
- `###` = nível 3 (detalhe — título)
- Conteúdo abaixo de `###` = corpo do detalhe, exibido no modal ao clicar

### Tabela `library_items` — nova

```sql
CREATE TABLE library_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('video', 'pdf', 'document', 'other')),
    url TEXT,
    file_path TEXT,
    image_path TEXT,
    subtitle_path TEXT,
    metadata TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_library_items_project ON library_items(project_id);
```

| Campo | Descrição |
|-------|-----------|
| `name` | Nome de exibição ("Aula 3 - Fundações") |
| `type` | `video`, `pdf`, `document`, `other` |
| `url` | URL externa (YouTube, Vimeo, etc). Nullable |
| `file_path` | Path local relativo em `midias/`. Nullable |
| `image_path` | Thumbnail/capa do item. Nullable |
| `subtitle_path` | Path local do arquivo de legendas (.srt, .vtt). Nullable |
| `metadata` | JSON livre (duração, idioma, tags, transcrição) |
| `position` | Ordem de exibição na biblioteca |

Pelo menos `url` ou `file_path` deve estar preenchido.

### Remoção

- Tabela `project_images` — não é removida nesta fase (já existe no schema)
- Não há tabela de coleções no banco (eram apenas mock data)

### Migration

Uma única migration que:
1. Adiciona `content_md` à tabela `projects`
2. Cria tabela `library_items`
3. Seed: popula `content_md` dos projetos existentes com markdown de exemplo

---

## 2. Rotas e Navegação

### Rotas removidas
- `GET /projects/{project_id}` — removida
- `GET /projects/{project_id}/collections/{collection_id}` — removida

### Rotas mantidas (sem mudança)
- `GET /` — redireciona para `/{username}`
- `GET /{username}` — lista projetos do usuário

### Rotas novas/ajustadas
- **`GET /{username}/{shortname}`** — busca projeto pelo `shortname` + `username`, faz parse do `content_md`, renderiza accordion de tópicos
- **`GET /htmx/details/{username}/{shortname}/{detail_id}`** — retorna conteúdo markdown renderizado de um detalhe. O `detail_id` é o índice hierárquico derivado do parse (ex: `1.2.1`)

### Fluxo de navegação

```
/{username}                    → lista projetos (cards)
/{username}/{shortname}        → accordion com tópicos/subtópicos/detalhes
    clique no detalhe          → modal com conteúdo markdown renderizado
```

---

## 3. Parser de Markdown

### Função `parse_topics_md(content_md: str) -> list`

Recebe o markdown e retorna estrutura hierárquica:

```python
[
    {
        "title": "Tópico 1",
        "id": "1",
        "subtopics": [
            {
                "title": "Subtópico 1.1",
                "id": "1.1",
                "details": [
                    {
                        "title": "Detalhe 1.1.1",
                        "id": "1.1.1",
                        "content_md": "Texto markdown do detalhe...",
                        "has_content": True
                    }
                ]
            }
        ]
    }
]
```

### Regras de parsing
- Split por linhas, identifica headings pelo prefixo `#`, `##`, `###`
- `id` hierárquico gerado por contagem sequencial (1, 1.1, 1.1.1)
- Conteúdo entre um `###` e o próximo heading é o `content_md` do detalhe
- `has_content` é `True` se o detalhe tem conteúdo além do título
- Implementado com split por headings, sem dependência de lib externa

### Função `get_detail_content(content_md: str, detail_id: str) -> str`

Auxiliar que faz parse e retorna o `content_md` de um detalhe específico pelo `id` hierárquico.

### Renderização no modal
1. Backend localiza o detalhe pelo `id` hierárquico
2. Renderiza markdown para HTML (lib `markdown` já instalada)
3. Detecta links de YouTube no HTML e converte em iframe embed
4. Retorna fragment HTML para o modal

---

## 4. Limpeza de Coleções

### Código removido de `main.py`
- `_COLLECTION_COLORS` — array de cores de gradiente
- `MOCK_COLLECTIONS` — dicionário de coleções mock
- `_build_mock_topics()` — função que gera mock topics/subtopics/details
- `MOCK_TOPICS`, `MOCK_DETAILS` — dicionários de dados mock
- Rotas `GET /projects/{project_id}` e `GET /projects/{project_id}/collections/{collection_id}`

### Templates
- **`collections.html`** — deletado
- **`topics.html`** — adaptado para receber estrutura do parser em vez de mock data; rota muda para `/{username}/{shortname}`
- **`grid_page.html`** — mantido (usado por `home.html`)
- **`partials/detail_modal.html`** — adaptado para receber HTML renderizado do markdown

### Testes
- **`test_collections.py`** — deletado
- **`test_topics.py`** — reescrito para testar `/{username}/{shortname}` com `content_md` no banco
- **`test_dark_mode.py`** — removidos testes de coleções, mantidos os demais

### Docs
- Specs e plans antigos de coleções ficam como histórico

---

## 5. Biblioteca — Detalhes

### Funcionalidade nesta fase
Apenas **schema + seed data**. Sem CRUD, sem UI, sem processamento LLM.

### Relação com projetos
- Cada projeto tem exatamente 1 biblioteca (conjunto de `library_items` com `project_id`)
- A biblioteca é o repositório de materiais fonte (input)
- Na próxima fase, ao adicionar itens na biblioteca, o sistema usará LLM para resumir, classificar e gerar/ajustar os tópicos (`content_md`)

### Campos

| Campo | Uso |
|-------|-----|
| `name` | Nome de exibição do item |
| `type` | `video`, `pdf`, `document`, `other` |
| `url` | URL externa (YouTube, Vimeo). Nullable |
| `file_path` | Path local em `midias/`. Nullable |
| `image_path` | Thumbnail/capa. Nullable |
| `subtitle_path` | Legendas (.srt, .vtt). Nullable |
| `metadata` | JSON livre (duração, idioma, tags, transcrição) |
| `position` | Ordem de exibição |
