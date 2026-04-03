# Public Subjects Access — Design Spec

**Date:** 2026-04-03
**Status:** Draft

## Goal

Assuntos marcados como públicos devem ser acessíveis sem login. A biblioteca aparece em modo read-only para não-donos; controles de edição ficam disponíveis apenas para o proprietário.

## Approach

Rotas duais — as mesmas URLs (`/{username}`, `/{username}/{shortname}`) servem tanto visitantes quanto donos. Uma dependência `get_optional_user` retorna o user ou `None` sem redirecionar. O template recebe `is_owner` (bool) para controlar a UI.

## 1. Autenticação opcional

### Nova dependência: `get_optional_user`

Em `app/auth.py`, criar `get_optional_user(request, db)` que:
- Lê o cookie `session_token`
- Se válido, retorna o dict do user (mesmo formato de `get_current_user`)
- Se ausente ou expirado, retorna `None` (sem redirect, sem erro)

### Rotas afetadas

| Rota | Dependência atual | Nova dependência |
|------|-------------------|------------------|
| `GET /` | `require_auth` | `optional_user` |
| `GET /{username}` | `require_auth` | `optional_user` |
| `GET /{username}/{shortname}` | `require_auth` | `optional_user` |

Todas as rotas HTMX de escrita (POST/PUT/DELETE) permanecem com `require_auth`.

## 2. Lógica de visibilidade

### `GET /` — Landing page ou redirect

- Se logado: redirect para `/{username}` (comportamento atual)
- Se não logado: renderiza `landing.html`

### `GET /{username}` — Lista de assuntos

- Query busca o user pelo username. Se não existe: 404.
- Se o visitante é o dono (`user and user.id == profile_user.id`): mostra todos os assuntos (como hoje).
- Se não é o dono ou não logado: mostra apenas assuntos com `is_public = 1`. Se não houver nenhum, exibe a página normalmente com mensagem "Nenhum assunto público" (não 404).
- Template recebe `is_owner` para controlar botões de criar/editar/excluir.

### `GET /{username}/{shortname}` — Detalhe do assunto

- Query busca o assunto pelo `shortname` + `owner_id` (via username).
- Se `is_public = 0` e o visitante não é o dono: retorna 404 (não revelar existência).
- Se `is_public = 1` ou visitante é o dono: renderiza normalmente.
- Template recebe `is_owner`.

## 3. Controle de UI — flag `is_owner`

### `topics.html` (detalhe do assunto)

**Quando `is_owner = true`** (sem mudanças no comportamento atual):
- Botão de adicionar item à biblioteca
- Botões de excluir/reclassificar em cada item
- Botão "reclassify all"
- Modal de edição do assunto (nome, imagem, público/privado)

**Quando `is_owner = false`:**
- Biblioteca visível em modo read-only: cards dos itens (thumbnail, título, tipo) sem botões de ação
- Tópicos visíveis normalmente (accordion completo com links funcionais)
- Links de YouTube com timestamp e referências de PDF funcionam normalmente
- Sem botão de adicionar, excluir, editar, reclassificar
- Sem modal de edição do assunto

### `home.html` (lista de assuntos)

**Quando `is_owner = false`:**
- Sem botão de criar novo assunto
- Sem botões de editar/excluir nos cards
- Cards dos assuntos públicos exibidos como links clicáveis

## 4. Landing page

Novo template `landing.html` para visitantes não logados em `/`:

- Header com logo + botões de login/registrar
- Barra de pesquisa centralizada no topo
- Grid de cards de assuntos públicos (thumbnail, nome, autor/username)
- Cada card linka para `/{username}/{shortname}`
- Ordenação padrão: mais recentes primeiro (`created_at DESC`)

### Pesquisa

- Nova rota: `GET /htmx/search?q=termo`
- Busca simples: `WHERE is_public = 1 AND name LIKE '%termo%'`
- Retorna partial com cards filtrados
- Sem paginação, sem filtros avançados

## 5. Segurança — rotas de escrita

Todas as rotas HTMX de escrita mantêm `require_auth` e verificam ownership explicitamente:

| Rota | Verificação |
|------|-------------|
| `POST /htmx/subjects` | auth obrigatório |
| `PUT /htmx/subjects/{id}` | auth + `owner_id == user.id` |
| `DELETE /htmx/subjects/{id}` | auth + `owner_id == user.id` |
| `POST /htmx/library/save` | auth + subject `owner_id == user.id` |
| `DELETE /htmx/library/{id}` | auth + ownership via subject |
| `POST /htmx/library/{id}/classify` | auth + ownership via subject |
| `POST /htmx/library/{id}/retry` | auth + ownership via subject |
| `POST /htmx/library/reclassify-all/{id}` | auth + ownership |
| `GET /htmx/library/{id}/status` | auth + ownership |

## Files to modify

- `app/auth.py` — adicionar `get_optional_user`
- `app/main.py` — alterar dependências das 3 rotas GET, adicionar lógica de visibilidade, adicionar rota `/htmx/search`, alterar rota `/`
- `app/templates/topics.html` — condicionais `is_owner` nos controles da biblioteca
- `app/templates/home.html` — condicionais `is_owner` nos botões de CRUD
- `app/templates/landing.html` — novo template (landing page com pesquisa)
- `app/templates/partials/library_item.html` — condicionais `is_owner` nos botões de ação
- `app/templates/partials/search_results.html` — novo partial para resultados de busca
