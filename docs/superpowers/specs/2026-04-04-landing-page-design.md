# Landing Page Design

**Data:** 2026-04-04
**Substitui:** `app/templates/landing.html` (página atual para usuários não logados)

---

## Visão Geral

Página de marketing "single page scroll" que apresenta o produto, os planos e um formulário de contato. Suporta dark e light mode. Inclui busca de assuntos públicos que redireciona para `/busca`.

A landing substitui a `landing.html` existente — exibida na rota `/` para visitantes não autenticados (comportamento atual mantido).

---

## Seções

### 1. Hero

**Layout:** Texto à esquerda, ilustração SVG à direita. Em mobile, empilha (texto em cima, ilustração embaixo).

**Fundo:** Gradiente sutil — teal claro → branco (light), teal escuro → neutral-900 (dark).

**Conteúdo:**
- **Título (h1):** "Transforme vídeos em conhecimento organizado"
- **Subtítulo (p):** "Nossa IA extrai, classifica e organiza automaticamente o conteúdo de vídeos do YouTube em uma biblioteca de conhecimento estruturada."
- **CTA principal:** Botão "Comece grátis" → `/register`
- **CTA secundário:** Link texto "Já tem conta? Entrar" → `/login`
- **Busca:** Campo de input abaixo dos CTAs, placeholder "Buscar assuntos públicos...", ao submeter redireciona para `/busca?q={valor}`

**Ilustração SVG (inline):** Composição estilizada mostrando um player de vídeo com setas apontando para uma árvore hierárquica (representando tópicos → subtópicos → ações). Cores brand teal, traços limpos, estilo flat/outline.

---

### 2. Como Funciona

**Layout:** Grid 2×2 em desktop (`md:grid-cols-2`), empilha em mobile. Fundo neutro (white / neutral-900 dark).

**4 blocos**, cada um com ícone SVG grande + título + descrição:

1. **"Adicione vídeos e PDFs"**
   - Ícone: play + documento
   - Texto: "Cole o link de um vídeo ou playlist do YouTube, envie PDFs, e nós fazemos o resto."

2. **"IA organiza pra você"**
   - Ícone: cérebro / engrenagem
   - Texto: "Nossa inteligência artificial extrai as legendas, identifica tópicos e cria uma árvore de conhecimento automaticamente."

3. **"Converse com seus vídeos e PDFs"**
   - Ícone: balão de chat
   - Texto: "Faça perguntas sobre o conteúdo da sua biblioteca e receba respostas baseadas nos seus próprios materiais."

4. **"Estude e compartilhe"**
   - Ícone: livro / compartilhar
   - Texto: "Navegue pelos tópicos organizados, encontre o trecho exato do vídeo e compartilhe assuntos publicamente."

**Estilo dos cards:** Borda sutil (`border-slate-200 dark:border-neutral-700`), sombra leve, `rounded-xl`, padding generoso.

---

### 3. Planos

**Layout:** 3 cards lado a lado em desktop (`md:grid-cols-3`), empilham em mobile.

#### Card "Gratuito"
- **Preço:** R$ 0
- **Badge:** nenhum
- **Benefícios:**
  - Buscar e navegar assuntos públicos
  - Acessar conteúdo compartilhado por link
  - Chat com seus materiais
- **CTA:** "Criar conta grátis" → `/register`

#### Card "Editor" (destaque)
- **Preço:** R$ 19,90/mês
- **Badge:** "1 mês grátis" (badge teal)
- **Benefícios:**
  - Tudo do Gratuito
  - Criar e editar biblioteca
  - Até 50 itens adicionados por mês
- **CTA:** "Testar grátis por 1 mês" → `/register?plan=editor`
- **Destaque visual:** Borda teal, leve elevação (shadow-lg), escala levemente maior (`scale-105`)

#### Card "Editor Pro"
- **Preço:** R$ 49,90/mês
- **Badge:** "Mais popular" (badge teal)
- **Benefícios:**
  - Tudo do Editor
  - Até 200 itens adicionados por mês
  - Suporte prioritário
- **CTA:** "Testar grátis por 1 mês" → `/register?plan=pro`

**Abaixo dos cards:** Texto discreto "Precisa de mais? Entre em contato" — clicável, abre o modal de contato.

---

### 4. Modal de Contato

**Trigger:** Link "Entre em contato" na seção de planos.

**Implementação:** Alpine.js `x-data` no escopo da landing, overlay escuro, modal centralizado.

**Conteúdo:**
- **Título:** "Fale conosco"
- **Campos:**
  - Nome (input text, obrigatório)
  - Email ou WhatsApp (input text, obrigatório)
  - Mensagem (textarea, obrigatório)
- **Botão:** "Enviar" — por enquanto, ao clicar fecha o modal e exibe toast/mensagem inline "Obrigado! Retornaremos em breve."
- **Botão fechar:** X no canto superior direito, mesmo estilo do `btn_icon` da gaveta (rounded-full, bg-white/neutral-700, border sutil)
- **Envio real:** não implementado nesta fase (apenas visual)

---

### 5. Footer

**Layout:** Uma linha horizontal. Fundo escuro sutil (`bg-slate-100 dark:bg-neutral-800`).

- **Esquerda:** Nome do app / logo
- **Centro:** Links "Entrar · Criar conta"
- **Direita:** © 2026

---

## Requisitos Técnicos

### Arquivos Envolvidos
- **Substituir:** `app/templates/landing.html` — reescrever completamente
- **Rota existente:** A rota `/` em `main.py` já renderiza `landing.html` para usuários não logados. Sem alteração na rota.
- **Nova rota:** `GET /busca` — página de busca de assuntos públicos (pode ser um placeholder simples nesta fase, com campo de busca que consulta assuntos por nome)

### Ilustrações SVG
- Todas inline no template (sem arquivos externos)
- Cores usando classes Tailwind para suportar dark/light mode
- Estilo flat/outline, traços limpos, paleta teal + neutral

### Dark/Light Mode
- Segue o sistema existente: classe `dark` no `<html>` via Alpine.js `themeManager()`
- Todos os elementos com variantes `dark:` do Tailwind
- Gradientes, SVGs, cards, tudo deve funcionar nos dois modos

### Responsividade
- Mobile-first: empilha tudo
- `md:` breakpoint para layouts lado a lado (hero, grid 2x2, cards de planos)

### Dependências
- Nenhuma nova — usa Tailwind (CDN), Alpine.js e HTMX já presentes no `base.html`
- O template estende `base.html` normalmente

### Busca (`/busca`)
- Nova rota `GET /busca` que recebe `?q=` como query param
- Consulta `subjects` onde `public = 1` e `name LIKE %q%`
- Renderiza lista de assuntos encontrados com link para `/{username}/{shortname}`
- Template simples, pode ser refinado depois

---

## Fora do Escopo (desta fase)

- Envio real do formulário de contato (salvar no banco / enviar email)
- Sistema de pagamento / checkout
- Lógica de limites por plano (50/200 itens)
- Parâmetro `?plan=` no registro (apenas o link é criado, o registro não diferencia planos ainda)
