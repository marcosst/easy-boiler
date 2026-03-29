# Design: Home Page — Header + Grade de Projetos

**Data:** 2026-03-29

## Visão Geral

Tela home da aplicação com header fixo no topo e área de conteúdo exibindo uma grade de projetos. Implementada com Tailwind CSS (via CDN), Alpine.js para o dropdown e Jinja2 como template engine.

---

## Header

- **Fundo:** branco (`bg-white`), borda inferior sutil (`border-b border-slate-200`), sombra leve (`shadow-sm`).
- **Layout:** `max-w-7xl` centralizado, altura fixa `h-16`, flex com `justify-between`.
- **Logo (esquerda):** `<img>` apontando para `/static/logo-rect.svg`.
- **Menu do usuário (direita):** pill clicável (`bg-slate-100`, `rounded-full`) contendo:
  - Avatar circular com iniciais do usuário (`bg-blue-600`, texto branco).
  - Nome do usuário em texto.
  - Ícone de chevron que rotaciona 180° quando o dropdown está aberto.

### Dropdown

Controlado por Alpine.js (`x-data="{ open: false }"`). Fecha ao clicar fora (`@click.outside`) ou pressionar Esc (`@keydown.escape`). Animação de entrada/saída com `x-transition`.

**Cabeçalho do dropdown:** avatar maior + nome + email do usuário.

**Itens:**
1. Meu Perfil — ícone de pessoa, link `href="/profile"`
2. Configurações — ícone de engrenagem, link `href="/settings"`
3. Separador
4. Sair — texto vermelho, link `href="/logout"`

---

## Área de Conteúdo

- **Container:** `max-w-7xl`, padding `px-6 py-8`, fundo `bg-slate-100`.
- **Título:** `<h1>` com texto "Projetos", `text-2xl font-bold text-slate-800`, margem inferior `mb-6`.
- **Grade:** CSS Grid responsivo — 1 coluna em mobile, 2 em `sm`, 3 em `lg`. Gap `gap-6`.

### Card de Projeto

- Fundo branco, `rounded-xl`, borda `border border-slate-200`, sombra leve com `hover:shadow-md` na interação.
- **Thumbnail:** `<div class="aspect-video">` (proporção 16:9) contendo `<img>` do projeto (ou placeholder de cor enquanto não há imagem real).
- **Rodapé:** padding `p-3` com `<span>` contendo o título do projeto (`text-sm font-medium text-slate-800`).
- Card inteiro é clicável (cursor pointer); link para a página do projeto.

---

## Dados (passados pelo template)

O contexto Jinja2 recebe uma variável `projects` — lista de objetos com:
- `id` — identificador do projeto
- `name` — nome exibido abaixo do card
- `thumbnail_url` — URL da imagem 16:9 (pode ser `None` para usar placeholder)

O usuário logado é passado via `user` com `name`, `email` e `initials`.

---

## Arquivos a criar/modificar

| Arquivo | Ação |
|---|---|
| `app/templates/base.html` | Adicionar CDN do Tailwind, remover CSS antigo do `<link>` |
| `app/templates/home.html` | Novo template com header + grade |
| `app/main.py` | Rota `GET /` retornando `home.html` com contexto `user` + `projects` |

> **Nota:** O CSS vanilla em `static/css/style.css` será desativado no `base.html` para evitar conflito com Tailwind. O arquivo em si não é deletado.

---

## Comportamento do Dropdown

- Estado inicial: fechado.
- Abre ao clicar no pill do usuário.
- Fecha ao: clicar fora do dropdown, pressionar Esc, ou clicar em qualquer item do menu.
- Animação: `opacity` + `scale` com duração 100ms entrada / 75ms saída.
