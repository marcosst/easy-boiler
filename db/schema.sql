CREATE TABLE IF NOT EXISTS "schema_migrations" (version varchar(128) primary key);
CREATE TABLE example (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
, language TEXT NOT NULL DEFAULT 'pt');
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
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    shortname    TEXT    NOT NULL UNIQUE
                         CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public    INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    owner_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
, image_path TEXT, content_md TEXT);
CREATE TABLE IF NOT EXISTS "subject_images" (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES "subjects"(id) ON DELETE CASCADE,
    filename   TEXT    NOT NULL,
    position   INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE library_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES "subjects"(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('video', 'pdf', 'document', 'other')),
    url TEXT,
    file_path TEXT,
    image_path TEXT,
    subtitle_path TEXT,
    metadata TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_subjects_owner ON subjects(owner_id);
CREATE INDEX idx_subject_images_subject ON subject_images(subject_id);
CREATE INDEX idx_library_items_subject ON library_items(subject_id);
-- Dbmate schema migrations
INSERT INTO "schema_migrations" (version) VALUES
  ('20240101000000'),
  ('20260329000000'),
  ('20260329222835'),
  ('20260329232616'),
  ('20260330013742'),
  ('20260330023233'),
  ('20260330031830');
