# Design: Migração content_md → content_json e Renderização de Tópicos

**Data:** 2026-03-30
**Status:** Aprovado

## Contexto

A tabela `subjects` atualmente armazena conteúdo em markdown no campo `content_md`, parseado por `md_parser.py` em árvore de tópicos → subtópicos → detalhes. O novo formato é JSON estruturado no campo `content_json`, onde cada passo referencia um `library_id` e contém metadados para abrir vídeos (com timestamp) ou PDFs (com página).

## Estrutura do JSON

Conforme `docs/topics_json_sample.json`:

```json
{
  "topicos": [
    {
      "titulo": "Nome do Tópico",
      "subtopicos": [
        {
          "titulo": "Nome do Subtópico",
          "passos": [
            {
              "library_id": 11,
              "acao": "Texto descritivo do passo",
              "timestamp": "00:00:30",
              "pagina": null,
              "trecho_referencia": "",
              "file_path": null,
              "url": "https://youtube.com/watch?v=abc123"
            }
          ]
        }
      ]
    }
  ]
}
```

Campos de cada passo:
- `library_id` (int) — referência ao `library_items.id` para limpeza em cascata
- `acao` (string) — texto exibido, clicável
- `timestamp` (string|null) — formato "HH:MM:SS", usado para posicionar vídeo
- `pagina` (int|null) — número da página para preview de PDF
- `trecho_referencia` (string) — texto secundário de apoio
- `file_path` (string|null) — caminho do documento (ex: `/midias/marcosst/manual.pdf`)
- `url` (string|null) — URL do vídeo (YouTube)

Um passo tem `url` (vídeo) OU `file_path` (documento), nunca ambos.

## 1. Migration

Nova migration que faz substituição direta via recriação de tabela (padrão SQLite):

1. Criar `subjects_new` com `content_json TEXT` no lugar de `content_md TEXT`
2. Copiar dados de `subjects` para `subjects_new` (campo `content_json` recebe `NULL`)
3. Dropar `subjects`
4. Renomear `subjects_new` para `subjects`
5. Recriar índice `idx_subjects_owner`

O `-- migrate:down` faz o inverso (recria `content_md`, perde `content_json`).

Dados existentes em `content_md` são descartados — não há conversão automática.

## 2. Parser

Remove `app/md_parser.py` por completo.

Nova função `parse_topics_json(content_json: str | None) -> list[dict]` — pode ficar em `app/main.py` ou num módulo utilitário simples.

- Recebe a string JSON do campo `content_json`
- Se `None` ou vazia, retorna lista vazia
- Faz `json.loads()` e retorna `data["topicos"]`
- O template itera diretamente sobre a estrutura retornada

Funções removidas: `parse_topics_md()`, `get_detail_content()`.

## 3. Template — Renderização

O template `app/templates/topics.html` mantém a mesma estrutura visual de accordions colapsáveis em 3 níveis:

### Árvore de tópicos

- **Nível 1 — Tópico:** accordion com `topico.titulo`
- **Nível 2 — Subtópico:** accordion com `subtopico.titulo`
- **Nível 3 — Passo:** item de lista com texto de `passo.acao`, clicável

### Comportamento do clique no passo

- **Se `passo.url` presente** → abre modal de vídeo com iframe YouTube embed. Se `passo.timestamp` existe, converte "HH:MM:SS" para segundos e passa como `?start=N` no URL do embed.
- **Se `passo.file_path` presente** → abre modal com `<embed src="file_path#page=N" type="application/pdf">` onde N vem de `passo.pagina`.
- **`trecho_referencia`**, se presente, aparece como texto secundário (cinza, fonte menor) abaixo da `acao`.

### Modal

Reutiliza e expande o modal de biblioteca existente (componente Alpine.js):
- Estado: `type` ('video' | 'pdf'), `url`, `name`
- **Vídeo:** iframe YouTube embed (já funciona hoje)
- **PDF:** `<embed>` com `type="application/pdf"`, tamanho generoso (ex: `w-full h-[80vh]`), URL com `#page=N`

## 4. Rotas

### Removida
- `GET /htmx/details/{username}/{shortname}/{detail_id}` — não há mais conteúdo markdown para buscar server-side

### Alterada
- `GET /{username}/{shortname}` — a rota de tópicos agora chama `parse_topics_json(subject["content_json"])` em vez de `parse_topics_md(subject["content_md"])`. Passa o resultado como `topicos` para o template.

## 5. Seed Script

Script `scripts/seed.py` executável com `python scripts/seed.py`.

Usa `sqlite3` síncrono. Busca o usuário "marcos@medire.com.br" pelo email; se não existir, cria com username "marcosst" e senha hash padrão.

### Dados gerados

**Subjects (6):**
1. "Cadastro de Componentes" (shortname: `cadastro-componentes`)
2. "Montagem de Módulos" (shortname: `montagem-modulos`)
3. "Configuração de Ferragens" (shortname: `configuracao-ferragens`)
4. "Renderização 3D" (shortname: `renderizacao-3d`)
5. "Orçamento e Propostas" (shortname: `orcamento-propostas`)
6. "Instalação em Obra" (shortname: `instalacao-obra`)

**Library items (5-6 por subject):** mistura de tipos `video` (com URLs YouTube fictícias) e `pdf` (com `file_path` em `/midias/marcosst/`).

**content_json:** cada subject terá 2-3 tópicos, 2-3 subtópicos por tópico, 2-4 passos por subtópico. Os `library_id`s nos passos referenciam os IDs dos library items inseridos. Estrutura idêntica ao `docs/topics_json_sample.json`.

## 6. Limpeza

- Remove `app/md_parser.py`
- Remove rota `/htmx/details/{username}/{shortname}/{detail_id}` de `app/main.py`
- Remove import de `markdown` e dependência do pacote se não usada em outro lugar
- Remove template `app/templates/partials/detail_modal.html`
- Remove referências a `content_md` nos templates e rotas

## Arquivos Afetados

| Arquivo | Ação |
|---------|------|
| `db/migrations/YYYYMMDD_content_json.sql` | Novo — migration |
| `app/md_parser.py` | Removido |
| `app/main.py` | Alterado — nova função parser, rota de tópicos atualizada, rota de detalhes removida |
| `app/templates/topics.html` | Alterado — renderiza a partir de JSON, modal expandido para PDF |
| `app/templates/partials/detail_modal.html` | Removido |
| `scripts/seed.py` | Novo — seed de dados de exemplo |
| `pyproject.toml` | Possivelmente alterado — remover dep `markdown` |
