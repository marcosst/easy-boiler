# Tela de Projetos — De Mockup para Dados Reais

**Data:** 2026-03-29
**Status:** Aprovado

## Objetivo

Transformar a tela de projetos (home) de mockup com dados hardcoded para uma tela real que busca projetos do banco de dados SQLite, filtrados pelo usuário logado. Inclui reestruturação de rotas para usar `/{username}` e seed de dados fake para teste.

## 1. Migration — `image_path` + seed

Nova migration dbmate:

**Up:**
- `ALTER TABLE projects ADD COLUMN image_path TEXT` (nullable)
- Inserir 5 projetos fake vinculados ao usuário `marcos@medire.com.br` (via subquery no `owner_id`):
  - "Reforma Apartamento 302" / `reforma-apartamento-302`
  - "Orcamento Obra Centro" / `orcamento-obra-centro`
  - "Residencial Vila Nova" / `residencial-vila-nova`
  - "Projeto Fachada Comercial" / `projeto-fachada-comercial`
  - "Levantamento Terreno Sul" / `levantamento-terreno-sul`
- Todos com `is_public = 0`, `image_path = NULL`
- Shortnames devem ser globalmente unicos (constraint UNIQUE ja existe na tabela)

**Down:**
- Deletar os projetos inseridos (por shortname)
- Remover coluna `image_path` (SQLite requer recrear tabela ou usar versao que suporte DROP COLUMN)

## 2. Rotas

### `GET /`
- Se usuario logado: redireciona para `/{username}` (HTTP 303)
- Se nao logado: redireciona para `/auth/login`

### `GET /{username}`
- Busca usuario pelo username
- Se nao encontrar: 404
- Se encontrar: busca projetos do usuario no banco:
  ```sql
  SELECT id, name, shortname, image_path, created_at
  FROM projects WHERE owner_id = ? ORDER BY created_at DESC
  ```
- Renderiza `home.html` com os projetos reais
- Contexto do template: `user` (logado), `profile_user` (dono da pagina), `projects` (lista)

### `GET /{username}/{shortname}` (futuro, nao implementar agora)
- Links dos cards ja apontam para esta URL
- Sera implementado quando migrarmos as telas internas

### Conflito de rotas
- Rotas fixas (`/auth/*`, `/static/*`, `/htmx/*`, etc.) sao registradas antes
- `/{username}` e catch-all, mas so resolve se existir usuario com aquele username; caso contrario, 404

## 3. Template — gradiente dinamico

O template `home.html` mantem a estrutura atual. Mudancas:

- **Gradiente por ID:** paleta de ~8 gradientes Tailwind, selecionado por `project.id % 8`
- **Imagem real:** quando `project.image_path` tem valor, renderiza `<img src="/midias/{{ project.image_path }}">`
- **Links:** cards apontam para `/{{ user.username }}/{{ project.shortname }}`
- **Menu 3 pontos:** mantido visualmente, sem funcionalidade (futuro)

Paleta de gradientes:
```
0: bg-gradient-to-br from-teal-400 to-teal-700
1: bg-gradient-to-br from-blue-400 to-blue-700
2: bg-gradient-to-br from-purple-400 to-purple-700
3: bg-gradient-to-br from-rose-400 to-rose-700
4: bg-gradient-to-br from-amber-400 to-amber-700
5: bg-gradient-to-br from-emerald-400 to-emerald-700
6: bg-gradient-to-br from-cyan-400 to-cyan-700
7: bg-gradient-to-br from-indigo-400 to-indigo-700
```

## 4. Pasta `midias/` e serving estatico

- Criar pasta `midias/` na raiz do projeto
- Montar no FastAPI: `app.mount("/midias", StaticFiles(directory="midias"), name="midias")`
- Adicionar criacao da pasta no `Makefile` target `setup`
- Nenhuma imagem sera servida agora (todos projetos fake tem `image_path = NULL`)

## 5. Fora do escopo

- Rota `GET /{username}/{shortname}` (tela interna do projeto)
- Upload de imagem
- Funcionalidade dos botoes do menu (Renomear, Trocar imagem, Excluir)
- Botao "Novo Projeto"
- Logica de geracao de shortname com sufixo anti-duplicata
