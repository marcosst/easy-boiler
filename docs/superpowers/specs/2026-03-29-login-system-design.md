# Login System Design

## Overview

Authentication system for the easy-boiler app with email/password login, account registration, and OAuth2 social login (Google, GitHub, Microsoft). Uses server-side sessions with httponly cookies.

## UI Style

Fullscreen minimalista (sem card container). Formulário centralizado na tela com fundo escuro (#171717 em dark mode). Layout B: email/senha primeiro, botões sociais como ícones compactos embaixo separados por divider "ou continue com".

## Routes

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/login` | GET | public | Render login page |
| `/login` | POST | public | Authenticate email+password, create session, redirect to `/` |
| `/register` | GET | public | Render registration page |
| `/register` | POST | public | Create local account, create session, redirect to `/` |
| `/logout` | GET | authenticated | Destroy session, redirect to `/login` |
| `/auth/{provider}` | GET | public | Initiate OAuth2 flow (google, github, microsoft) |
| `/auth/{provider}/callback` | GET | public | OAuth2 callback — create/link account, create session |
| `/auth/choose-username` | GET | partial (temp session) | Render username selection (post-OAuth new accounts) |
| `/auth/choose-username` | POST | partial (temp session) | Save username, finalize account, redirect to `/` |

Protected routes (all existing routes: `/`, `/projects/*`) redirect to `/login` when no valid session exists.

## Database Schema

### Table: `users`

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| username | TEXT | NOT NULL, UNIQUE |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NULLABLE (null for OAuth-only accounts) |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

### Table: `sessions`

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FK → users(id) ON DELETE CASCADE |
| token | TEXT | NOT NULL, UNIQUE |
| expires_at | DATETIME | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

Index on `token` for fast lookups.

### Table: `oauth_accounts`

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FK → users(id) ON DELETE CASCADE |
| provider | TEXT | NOT NULL (google, github, microsoft) |
| provider_user_id | TEXT | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

Unique constraint on `(provider, provider_user_id)`.

## Business Rules

### Username
- Lowercase only, allowed chars: `[a-z0-9-]`
- Must be unique
- Validated on both frontend (pattern attribute) and backend (regex)

### Password
- Hashed with bcrypt via `passlib`
- No minimum length enforced for now (can be added later)

### Sessions
- Token generated with `secrets.token_urlsafe(32)`
- Stored in httponly cookie named `session_token`
- Expires in 30 days
- Checked on every protected route via FastAPI dependency

### OAuth Flow
1. User clicks social icon → `GET /auth/{provider}` → redirect to provider
2. Provider authenticates → redirects to `/auth/{provider}/callback`
3. Backend exchanges code for user info (email, provider_user_id)
4. If email matches existing user → link OAuth account, create session, redirect `/`
5. If no existing user → store OAuth data in temporary session, redirect `/auth/choose-username`
6. User picks username → create user + OAuth account, create session, redirect `/`

### Auth Middleware
- FastAPI dependency `get_current_user(request)` reads `session_token` cookie
- Looks up session in DB, checks expiry
- Returns user dict or None
- Protected routes use `require_auth` dependency that redirects to `/login` if None

## Templates

### `login.html`
- Fullscreen, centered, no card
- Logo "resumiu" + subtitle "Entre na sua conta"
- Email input, password input, "Entrar" button (teal #26a69a)
- Divider "ou continue com"
- 3 icon buttons in row: Google, GitHub, Microsoft (48x48, bordered)
- Footer link: "Não tem conta? Criar conta" → `/register`
- Error messages displayed inline above form

### `register.html`
- Same fullscreen style
- Logo + subtitle "Crie sua conta"
- Username input (with hint "Apenas letras minúsculas, números e hífens")
- Email input, password input, confirm password input
- "Criar conta" button
- Divider + social icons (same as login)
- Footer link: "Já tem conta? Entrar" → `/login`

### `choose_username.html`
- Same fullscreen style
- Logo + subtitle "Escolha seu username"
- Username input with validation hint
- "Continuar" button
- Shown only after OAuth signup when no account exists

## Dependencies

New packages to add to `pyproject.toml`:

- `authlib` — OAuth2 client for Google, GitHub, Microsoft
- `passlib[bcrypt]` — password hashing with bcrypt
- `httpx` — already in dev deps, needed by authlib for async HTTP

## Environment Variables

New entries for `.env` and `.env.example`:

```
SECRET_KEY=<random-secret-for-session-signing>

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `db/migrations/YYYYMMDD_create_auth_tables.sql` | create | Migration for users, sessions, oauth_accounts |
| `app/auth.py` | create | Auth logic: password hashing, session management, OAuth config, dependencies |
| `app/main.py` | modify | Add auth routes, protect existing routes with `require_auth` |
| `app/templates/login.html` | create | Login page template |
| `app/templates/register.html` | create | Registration page template |
| `app/templates/choose_username.html` | create | Post-OAuth username selection |
| `app/templates/partials/header.html` | modify | Use real user data from session instead of MOCK_USER |
| `.env.example` | modify | Add auth-related env vars |
| `pyproject.toml` | modify | Add authlib, passlib[bcrypt] |
