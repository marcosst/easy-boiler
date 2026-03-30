# i18n — Seletor de Idioma (EN/PT/ES)

## Resumo

Adicionar suporte a múltiplos idiomas (inglês, português, espanhol) com seletor de idioma no menu do usuário e nas páginas públicas. Todas as strings hardcoded em português serão extraídas para arquivos JSON de tradução, acessíveis via função global `_()` no Jinja2.

## Decisões de Design

| Aspecto | Decisão |
|---------|---------|
| Persistência | Banco (`users.language`) + cookie `lang` |
| Idioma padrão | Auto-detect via `Accept-Language`, fallback `pt` |
| Catálogo de traduções | Arquivos JSON por idioma (`en.json`, `pt.json`, `es.json`) |
| Acesso nos templates | Função global Jinja2 `_()` |
| Seletor (logado) | Bandeirinhas inline (🇺🇸 🇧🇷 🇪🇸) no menu do usuário, entre "Tema" e "Sair" |
| Seletor (público) | Bandeirinhas no canto superior direito das páginas de login/register |

## Estrutura de Arquivos

```
app/
  i18n/
    __init__.py    — carrega JSONs, expõe _(), registra global no Jinja2
    en.json        — traduções inglês
    pt.json        — traduções português (base)
    es.json        — traduções espanhol
  templates/
    partials/
      language_selector.html  — componente reutilizável das bandeirinhas
```

## Arquivos JSON de Tradução

Chaves flat com namespace por contexto:

```json
{
  "header.profile": "My Profile",
  "header.settings": "Settings",
  "header.theme": "Theme",
  "header.language": "Language",
  "header.logout": "Sign out",
  "header.light": "Light",
  "header.dark": "Dark",
  "header.auto": "Auto",
  "home.subjects": "Subjects",
  "home.new_subject": "New Subject",
  "home.rename": "Rename",
  "home.change_image": "Change image",
  "home.delete": "Delete",
  "topics.topics": "Topics",
  "topics.library": "Library",
  "topics.add_content": "Add content",
  "topics.close_chat": "Close chat",
  "topics.close_library": "Close library",
  "topics.chat_placeholder": "Ask a question...",
  "topics.chat_greeting": "Hello! I'm your study assistant. Ask me anything about this subject.",
  "topics.chat_about": "Chat about this subject",
  "topics.reload": "Reload",
  "topics.delete": "Delete",
  "login.title": "Sign in to your account",
  "login.email": "Email",
  "login.password": "Password",
  "login.submit": "Sign in",
  "login.or_continue": "or continue with",
  "login.no_account": "Don't have an account?",
  "login.create_account": "Create account",
  "login.invalid_credentials": "Invalid email or password.",
  "register.title": "Create your account",
  "register.username": "Username",
  "register.username_hint": "Lowercase letters, numbers, and hyphens only",
  "register.email": "Email",
  "register.password": "Password",
  "register.confirm_password": "Confirm password",
  "register.submit": "Create account",
  "register.or_continue": "or continue with",
  "register.has_account": "Already have an account?",
  "register.sign_in": "Sign in",
  "register.passwords_mismatch": "Passwords don't match.",
  "register.email_or_username_taken": "Email or username already in use.",
  "choose_username.title": "Choose your username",
  "choose_username.submit": "Continue",
  "choose_username.username_taken": "Username already in use."
}
```

O arquivo `pt.json` contém as strings atuais em português. O `es.json` contém as traduções em espanhol.

## Módulo i18n (`app/i18n/__init__.py`)

Responsabilidades:
- Carregar os 3 arquivos JSON na inicialização
- Expor função `_(key, lang=None)` que busca a tradução
- Se a chave não existir no idioma, fallback para `pt`; se não existir em `pt`, retorna a própria chave
- Registrar `_()` como global do Jinja2 no startup do app

A função `_()` nos templates usa `request.state.lang` automaticamente. No backend Python, o `lang` deve ser passado explicitamente.

## Resolução do Idioma (Middleware)

Um middleware FastAPI (`app/i18n/middleware.py` ou inline no `main.py`) que resolve o idioma em cada request, nesta ordem de prioridade:

1. **Query param `?lang=es`** — para troca explícita de idioma
2. **Cookie `lang`** — persistência cross-request (público e logado)
3. **Coluna `users.language`** — preferência salva do usuário logado
4. **Header `Accept-Language`** — auto-detect do browser (parse para encontrar en/pt/es)
5. **Fallback `pt`**

O idioma resolvido é setado em `request.state.lang`.

Quando o query param `?lang=X` está presente, o middleware também seta/atualiza o cookie `lang`.

## Troca de Idioma

### Usuário logado (menu)

As bandeirinhas no menu fazem um POST HTMX para `/htmx/set-language`:

```
POST /htmx/set-language
Body: lang=es
Response headers: HX-Refresh: true
```

A rota:
1. Atualiza `users.language` no banco
2. Seta cookie `lang=es`
3. Retorna resposta vazia com `HX-Refresh: true` para recarregar a página

### Páginas públicas (login/register)

As bandeirinhas são links simples: `?lang=en`, `?lang=pt`, `?lang=es`. O middleware detecta o query param, seta o cookie, e a página carrega no novo idioma.

## Migration

```sql
-- migrate:up
ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'pt';

-- migrate:down
ALTER TABLE users DROP COLUMN language;
```

Default `pt` para usuários existentes. No registro de novo usuário, salva o valor do cookie/`Accept-Language` como preferência inicial.

## Componente de Seletor (`partials/language_selector.html`)

Partial reutilizável que renderiza as 3 bandeirinhas. Recebe o idioma ativo de `request.state.lang` e destaca a bandeira correspondente (fundo roxo/indigo).

Usado em:
- `header.html` — dentro do dropdown do menu, entre "Tema" e "Sair"
- `login.html` — posicionado absoluto no canto superior direito
- `register.html` — posicionado absoluto no canto superior direito
- `choose_username.html` — posicionado absoluto no canto superior direito

## Templates Afetados

Todas as strings hardcoded em português serão substituídas por `{{ _('chave') }}`:

| Template | Strings a traduzir |
|----------|-------------------|
| `partials/header.html` | Meu Perfil, Configurações, Tema, Claro, Escuro, Auto, Sair + novo "Idioma" |
| `home.html` | Assuntos, Novo Assunto, Renomear, Trocar imagem, Excluir |
| `topics.html` | Tópicos, Biblioteca, Adicionar conteúdo, chat strings (~12 strings) |
| `login.html` | Entrar, Entre na sua conta, Email, Senha, etc. (~11 strings) |
| `register.html` | Criar Conta, Crie sua conta, campos, etc. (~10 strings) |
| `choose_username.html` | Escolha seu username, Continuar, etc. (~4 strings) |

## Mensagens de Erro no Backend

As mensagens de erro em `main.py` e `auth.py` também são traduzidas via `_()`:

- `login.invalid_credentials` — "Email ou senha incorretos."
- `register.passwords_mismatch` — "As senhas não coincidem."
- `register.email_or_username_taken` — "Email ou username já em uso."
- `choose_username.username_taken` — "Username já em uso."
- Validações de username em `auth.py`

## Fora de Escopo

- Tradução de conteúdo gerado pelo usuário (nomes de assuntos, tópicos, etc.)
- Tradução do conteúdo markdown dos tópicos
- RTL (right-to-left) layout
- Mais idiomas além de EN/PT/ES (estrutura suporta, mas não neste escopo)
