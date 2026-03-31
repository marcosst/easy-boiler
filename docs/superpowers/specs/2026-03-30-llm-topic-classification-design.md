# Design — Classificação de tópicos via LLM

**Data:** 2026-03-30
**Referência:** `docs/geração_dos_tópicos.md`

## Resumo

Após o download das legendas de um vídeo YouTube (via Apify), o sistema submete o transcript a uma LLM (OpenAI GPT-5.4) que classifica o conteúdo em tópicos/subtópicos/ações, reaproveitando taxonomia existente do subject. Os itens classificados são persistidos na tabela `knowledge_items` e a árvore consolidada é salva no `content_json` do subject, atualizando o accordion na tela em tempo real.

## Abordagem

Tudo síncrono, dividido em dois requests HTMX encadeados:

1. **Request 1** (`POST /htmx/library/save` — existente): Apify + save do library_item. Spinner: "Buscando legendas..."
2. **Request 2** (`POST /htmx/library/{id}/classify` — novo): LLM + persistência + rebuild da árvore. Spinner: "Fazendo a Mágica Acontecer..."

O request 1 retorna o item na biblioteca + um fragmento HTML invisível com `hx-trigger="load"` que dispara automaticamente o request 2. O modal fecha após request 1. O spinner de classificação aparece sobre/perto do accordion.

## Modelo de dados

### Nova tabela `knowledge_items`

```sql
CREATE TABLE knowledge_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id        INTEGER NOT NULL REFERENCES library_items(id) ON DELETE CASCADE,
    topico            TEXT NOT NULL,
    subtopico         TEXT NOT NULL,
    acao              TEXT NOT NULL,
    timestamp         TEXT,
    pagina            INTEGER,
    trecho_referencia TEXT NOT NULL DEFAULT '',
    file_path         TEXT,
    url               TEXT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_knowledge_items_library ON knowledge_items(library_id);
```

### Nova coluna em `library_items`

```sql
ALTER TABLE library_items ADD COLUMN processed_at DATETIME DEFAULT NULL;
```

### Regras de integridade (vídeo)

- `timestamp` não nulo, `url` não nula
- `pagina` nula, `file_path` nulo
- `trecho_referencia` = `""`

### Relação com `content_json`

Após persistir `knowledge_items`, a árvore consolidada é montada via query agrupando todos os `knowledge_items` do subject por `topico`/`subtopico`, e salva no `content_json` do subject. O accordion na tela é alimentado por esse JSON.

## Fluxo detalhado

### Request 1 — `/htmx/library/save` (modificações)

Fluxo existente inalterado (Apify → save library_item). Mudanças:

- Ao retornar o HTML do item, inclui fragmento auto-trigger:

```html
<div hx-post="/htmx/library/{id}/classify"
     hx-trigger="load"
     hx-target="#topics-accordion"
     hx-swap="innerHTML"
     hx-indicator="#classify-spinner">
</div>
```

- Trigger `close-add-modal` continua funcionando (modal fecha)

### Request 2 — `/htmx/library/{id}/classify` (novo)

1. Busca `library_item` pelo id (valida ownership)
2. Lê arquivo de legendas do disco via `subtitle_path`
3. Extrai taxonomia existente do subject (query `knowledge_items` agrupados)
4. Monta prompt com taxonomia + transcript
5. Chama OpenAI GPT-5.4 via `asyncio.to_thread()`
6. Valida resposta com Pydantic (`ResultadoLLM`)
7. Pós-processa: injeta `library_id`, monta URLs, define campos nulos
8. `DELETE FROM knowledge_items WHERE library_id = ?`
9. `INSERT` dos novos itens
10. Rebuild `content_json` do subject (query + agrupamento + UPDATE)
11. `UPDATE library_items SET processed_at = CURRENT_TIMESTAMP WHERE id = ?`
12. Retorna HTML do accordion atualizado

### Se a LLM falhar

- Item já está salvo na biblioteca (request 1 concluiu)
- `processed_at` permanece nulo
- Loga o erro
- Retorna accordion como estava (sem mudança)
- Elegível para reprocessamento futuro

## Módulos de código

### `app/services/llm_classifier.py`

- Monta prompt com taxonomia + transcript
- Chama OpenAI GPT-5.4 (`openai.chat.completions.create`)
- Chamada síncrona em thread via `asyncio.to_thread()` (padrão do app)
- Valida resposta com Pydantic
- Retorna lista de `ItemLLM`

### `app/services/taxonomy_service.py`

- Query `knowledge_items` do subject agrupados por topico/subtopico
- Retorna `{"topicos": [{"titulo": "...", "subtopicos": ["..."]}]}`
- Se não há items, retorna estrutura vazia

### `app/services/tree_builder.py`

- Query `knowledge_items` de um subject com `ORDER BY topico, subtopico, library_id, timestamp`
- Agrupa em árvore: `{"topicos": [{"titulo": "...", "subtopicos": [{"titulo": "...", "passos": [...]}]}]}`
- Cada passo tem: `library_id`, `acao`, `timestamp`, `pagina`, `trecho_referencia`, `file_path`, `url`
- Serializa e salva no `content_json` do subject

### `app/services/url_builder.py`

- `timestamp_to_seconds("00:01:03")` → `63`
- `build_step_url("abc123", "00:01:03")` → `https://www.youtube.com/watch?v=abc123&t=63s`

### `app/schemas/llm_output.py`

```python
class ItemLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topico: str = Field(min_length=1)
    subtopico: str = Field(min_length=1)
    acao: str = Field(min_length=1)
    timestamp: str = Field(pattern=r"^\d{2}:\d{2}:\d{2}$")

class ResultadoLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")
    itens: list[ItemLLM]
```

- Trim automático nos campos str
- Regex valida formato `HH:MM:SS`
- Rejeita campos extras

## Prompt da LLM

Segue fielmente o documento de referência:

- System message com regras de reutilização de taxonomia, normalização semântica, formato de saída
- User message com taxonomia existente (ou "Nenhuma taxonomia existente ainda.") + transcript formatado
- Pede retorno exclusivamente em JSON: `{"itens": [...]}`
- Não inclui `url`, `library_id`, `file_path`, `pagina` na saída da LLM — esses são injetados no pós-processamento

## Frontend

### Spinner de classificação

- Após fechar o modal (request 1), um indicador HTMX aparece próximo ao accordion
- Texto: "Fazendo a Mágica Acontecer..."
- Usa classe `htmx-indicator` padrão
- Desaparece automaticamente quando request 2 retorna

### Accordion atualizado

- Request 2 retorna o HTML do accordion re-renderizado server-side
- O `content_json` já foi atualizado no banco
- O target é `#topics-accordion` com `hx-swap="innerHTML"`

## Migração

Um arquivo dbmate com:

- `migrate:up`: CREATE TABLE `knowledge_items` + índice + ALTER TABLE `library_items` ADD COLUMN `processed_at`
- `migrate:down`: DROP TABLE `knowledge_items` + recreate `library_items` sem `processed_at`

## Tratamento de erros

| Cenário | Comportamento |
|---------|--------------|
| Chave OpenAI ausente | Loga erro, retorna accordion sem mudança |
| Timeout da OpenAI | Loga erro, retorna accordion sem mudança |
| Resposta JSON inválida | Loga erro, `processed_at` fica nulo |
| Pydantic rejeita payload | Loga erro, `processed_at` fica nulo |
| `library_item` não encontrado | 404 |
| `library_item` sem `subtitle_path` | Retorna sem processar |
| Erro no INSERT | Rollback, loga erro |

Em todos os casos de falha LLM, o item permanece salvo com `processed_at = NULL`.

## Reprocessamento (v1)

- Endpoint `POST /htmx/library/{id}/reprocess` — mesmo fluxo do classify, mas faz DELETE dos knowledge_items antigos antes
- Sem UI dedicada agora, endpoint pronto para uso futuro

## Dependências

- Adicionar `openai` ao `pyproject.toml`
- Chave `OPENAI_API_KEY` já presente no `.env`
- Modelo: `gpt-5.4`

## Fora do escopo

- Scanner de pasta (desnecessário — vídeos vêm via UI)
- CLI (app é web)
- Ingestão de PDF
- Retry automático da LLM
- Embeddings, RAG, busca semântica
- UI de reprocessamento
