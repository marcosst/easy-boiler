CREATE TABLE IF NOT EXISTS "schema_migrations" (version varchar(128) primary key);
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT     NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE TABLE oauth_accounts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider         TEXT    NOT NULL,
    provider_user_id TEXT    NOT NULL,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);
CREATE TABLE IF NOT EXISTS "subjects" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    shortname  TEXT    NOT NULL UNIQUE
                       CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public  INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    owner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    image_path TEXT,
    content_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_subjects_owner ON subjects(owner_id);
CREATE TABLE IF NOT EXISTS "library_items" (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id    INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    type          TEXT    NOT NULL CHECK(type IN ('youtube', 'pdf')),
    url           TEXT,
    file_path     TEXT,
    image_path    TEXT,
    subtitle_path TEXT,
    metadata      TEXT,
    position      INTEGER NOT NULL DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
, deleted_at DATETIME DEFAULT NULL, processed_at DATETIME DEFAULT NULL, status TEXT NOT NULL DEFAULT 'ready' CHECK(status IN ('pending', 'fetching', 'classifying', 'ready', 'error')));
CREATE INDEX idx_library_items_subject ON library_items(subject_id);
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
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK(type IN ('success', 'error', 'info')),
    message TEXT NOT NULL,
    seen INTEGER NOT NULL DEFAULT 0 CHECK(seen IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_notifications_user_unseen ON notifications(user_id, seen);
-- Dbmate schema migrations
INSERT INTO "schema_migrations" (version) VALUES
  ('20240101000000'),
  ('20260330200000'),
  ('20260330200001'),
  ('20260331000000'),
  ('20260331100000'),
  ('20260401233734'),
  ('20260401233742');
