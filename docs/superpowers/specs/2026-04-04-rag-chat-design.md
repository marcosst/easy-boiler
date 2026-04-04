# RAG Chat com sqlite-vec — Design Spec

## Contexto

A plataforma permite que usuários criem subjects (módulos de aprendizado) e adicionem vídeos do YouTube. O worker extrai legendas e classifica o conteúdo em tópicos/subtópicos/ações via LLM. Atualmente não há como o usuário fazer perguntas em linguagem natural sobre o conteúdo dos vídeos. Este design adiciona um chat RAG por subject, usando sqlite-vec como vector store.

## Decisões

- **Vector store:** sqlite-vec (extensão SQLite) — mantém a stack simples, sem serviço extra
- **Conteúdo indexado:** Legendas completas dos vídeos (texto bruto)
- **Escopo do chat:** Por subject (cada subject tem seu próprio contexto de busca)
- **UX:** Streaming via SSE (resposta aparece gradualmente)
- **Modelo de embedding:** OpenAI `text-embedding-3-small` (1536 dimensões)

## Arquitetura

### Pipeline de Indexação (write path)

```
Worker processa vídeo
  → Legendas extraídas (já existe)
  → Chunking: dividir legenda em chunks de ~500 tokens, overlap ~50 tokens
  → Cada chunk preserva: timestamp_start, timestamp_end, library_item_id
  → Gerar embedding via OpenAI text-embedding-3-small
  → Armazenar chunk + embedding no SQLite (content_chunks + vec_chunks)
```

Etapa adicionada ao worker existente (`app/worker.py`), após a extração de legendas e antes/em paralelo com a classificação LLM.

### Pipeline de Consulta (read path)

```
Usuário digita pergunta no chat do subject
  → POST /htmx/chat/{subject_id}
  → Gerar embedding da pergunta
  → Busca vetorial em vec_chunks filtrada por subject_id (top-5)
  → Montar prompt: system prompt + chunks relevantes + pergunta
  → Chamar OpenAI GPT com streaming
  → Retornar resposta via SSE com referências aos vídeos
```

## Schema do Banco

### Nova tabela: `content_chunks`

```sql
CREATE TABLE content_chunks (
    id INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    library_item_id INTEGER NOT NULL REFERENCES library_items(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    timestamp_start TEXT,  -- HH:MM:SS
    timestamp_end TEXT,    -- HH:MM:SS
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_content_chunks_subject ON content_chunks(subject_id);
CREATE INDEX idx_content_chunks_library_item ON content_chunks(library_item_id);
```

### Tabela virtual sqlite-vec: `vec_chunks`

```sql
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[1536]
);
```

O `chunk_id` referencia `content_chunks.id`. A busca vetorial retorna IDs que são então joined com `content_chunks` para obter texto e metadados.

## Chunking

- **Tamanho:** ~500 tokens por chunk (aproximadamente 2000 caracteres)
- **Overlap:** ~50 tokens entre chunks consecutivos (para não perder contexto nas bordas)
- **Preservação de timestamps:** Cada chunk mapeia para um intervalo de timestamps da legenda original
- **Formato da legenda:** As legendas já estão em formato texto plano em `midias/{username}/subtitles/{video_id}.txt`

### Novo serviço: `app/services/chunking_service.py`

Responsabilidades:
- Receber texto da legenda + metadados do vídeo
- Dividir em chunks com overlap
- Mapear timestamps para cada chunk (quando disponível na legenda)
- Retornar lista de chunks prontos para embedding

## Embeddings

### Novo serviço: `app/services/embedding_service.py`

Responsabilidades:
- Gerar embeddings via OpenAI `text-embedding-3-small`
- Batch processing (enviar múltiplos chunks numa chamada só — a API aceita até 2048 inputs)
- Armazenar na tabela `vec_chunks`

Usa o mesmo client OpenAI já configurado em `app/services/llm_classifier.py`.

## Chat Backend

### Nova rota: `POST /htmx/chat/{subject_id}`

```
Request: { "question": "Como inserir um puxador?", "history": [...] }
Response: SSE stream com HTML fragments
```

### Novo serviço: `app/services/rag_service.py`

Responsabilidades:
- Gerar embedding da pergunta
- Buscar top-5 chunks mais similares via sqlite-vec (filtrados por subject_id)
- Montar prompt com contexto
- Chamar OpenAI GPT com streaming
- Formatar referências (links para vídeos com timestamps)

### Prompt Template

```
Você é um assistente que responde perguntas sobre {subject_name}.
Use APENAS o contexto fornecido abaixo para responder.
Se não souber a resposta com base no contexto, diga que não encontrou informação sobre isso.

Sempre inclua referências aos vídeos quando citar informações.

--- Contexto ---
{chunks com metadados de vídeo e timestamps}
--- Fim do Contexto ---

Pergunta: {question}
```

## Interface (Frontend)

### Localização

Seção de chat na página do subject (`/{username}/{shortname}`), abaixo do accordion de tópicos.

### Componentes

- **Chat container:** Área de mensagens com scroll
- **Input:** Campo de texto + botão enviar
- **Mensagens do usuário:** Alinhadas à direita, estilo bubble
- **Mensagens do assistente:** Alinhadas à esquerda, com referências clicáveis
- **Referências:** Links para vídeos no formato "📎 {título} - {timestamp}", clicáveis

### Template

- `app/templates/partials/chat.html` — componente de chat (HTMX)
- `app/templates/partials/chat_message.html` — mensagem individual

### Streaming (SSE)

- Frontend usa `EventSource` (ou htmx `hx-ext="sse"`) para receber tokens
- Cada evento SSE contém um fragment HTML que é appended ao container
- Evento final inclui as referências formatadas

### Histórico da conversa

- Mantido no browser via JavaScript (array de mensagens)
- Enviado junto com cada pergunta para manter contexto conversacional
- Limitado às últimas 5 trocas para não estourar o contexto da LLM
- Não persistido no banco (se o usuário recarregar a página, o histórico é perdido)

## Dependências Novas

```toml
# pyproject.toml
"sqlite-vec>=0.1.6"
```

Nota: `sqlite-vec` é instalado via pip e carregado como extensão SQLite em runtime. Com `aiosqlite`, o carregamento da extensão deve ser feito via `await db.execute("SELECT load_extension('vec0')")` após habilitar extensões com `conn.enable_load_extension(True)` no objeto de conexão subjacente. Verificar compatibilidade na implementação.

## Modificações em Arquivos Existentes

| Arquivo | Modificação |
|---------|-------------|
| `app/database.py` | Carregar extensão sqlite-vec na conexão |
| `app/worker.py` | Adicionar etapa de chunking + embedding após extração de legendas |
| `app/main.py` | Adicionar rota `POST /htmx/chat/{subject_id}` e rota SSE |
| `app/templates/topics.html` | Adicionar seção de chat abaixo do accordion |
| `pyproject.toml` | Adicionar dependência `sqlite-vec` |
| `db/migrations/` | Nova migration para `content_chunks` e `vec_chunks` |

## Arquivos Novos

| Arquivo | Propósito |
|---------|-----------|
| `app/services/chunking_service.py` | Divisão de legendas em chunks com timestamps |
| `app/services/embedding_service.py` | Geração e armazenamento de embeddings |
| `app/services/rag_service.py` | Busca vetorial + montagem de prompt + chamada LLM |
| `app/templates/partials/chat.html` | Componente de chat HTMX |
| `app/templates/partials/chat_message.html` | Template de mensagem individual |

## Verificação

1. **Indexação:** Adicionar um vídeo a um subject, verificar que chunks e embeddings são criados no banco
2. **Busca:** Fazer uma pergunta no chat e verificar que os chunks retornados são relevantes
3. **Referências:** Verificar que os links para vídeos apontam para o timestamp correto
4. **Streaming:** Verificar que a resposta aparece gradualmente no browser
5. **Isolamento:** Verificar que o chat de um subject não retorna conteúdo de outro
6. **Delete cascade:** Verificar que ao deletar um library_item, seus chunks e embeddings são removidos
