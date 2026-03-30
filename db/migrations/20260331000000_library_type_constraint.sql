-- migrate:up

CREATE TABLE library_items_new (
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
);

INSERT INTO library_items_new (id, subject_id, name, type, url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at)
SELECT id, subject_id, name,
       CASE WHEN type = 'video' THEN 'youtube' ELSE type END,
       url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at
FROM library_items;

DROP TABLE library_items;
ALTER TABLE library_items_new RENAME TO library_items;

CREATE INDEX idx_library_items_subject ON library_items(subject_id);

-- migrate:down

CREATE TABLE library_items_old (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id    INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    type          TEXT    NOT NULL CHECK(type IN ('video', 'pdf', 'document', 'other')),
    url           TEXT,
    file_path     TEXT,
    image_path    TEXT,
    subtitle_path TEXT,
    metadata      TEXT,
    position      INTEGER NOT NULL DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO library_items_old (id, subject_id, name, type, url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at)
SELECT id, subject_id, name,
       CASE WHEN type = 'youtube' THEN 'video' ELSE type END,
       url, file_path, image_path, subtitle_path, metadata, position, created_at, updated_at
FROM library_items;

DROP TABLE library_items;
ALTER TABLE library_items_old RENAME TO library_items;

CREATE INDEX idx_library_items_subject ON library_items(subject_id);
