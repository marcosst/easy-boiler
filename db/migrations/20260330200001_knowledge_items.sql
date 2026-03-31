-- migrate:up
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

ALTER TABLE library_items ADD COLUMN processed_at DATETIME DEFAULT NULL;

-- migrate:down
DROP TABLE IF EXISTS knowledge_items;

-- SQLite doesn't support DROP COLUMN before 3.35.0, so we recreate:
CREATE TABLE library_items_backup AS SELECT id, subject_id, name, type, url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at, deleted_at FROM library_items;
DROP TABLE library_items;
CREATE TABLE library_items (
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
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at    DATETIME DEFAULT NULL
);
INSERT INTO library_items SELECT * FROM library_items_backup;
DROP TABLE library_items_backup;
CREATE INDEX idx_library_items_subject ON library_items(subject_id);
