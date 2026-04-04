-- migrate:up

CREATE TABLE content_chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id      INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    library_item_id INTEGER NOT NULL REFERENCES library_items(id) ON DELETE CASCADE,
    chunk_text      TEXT    NOT NULL,
    chunk_index     INTEGER NOT NULL,
    timestamp_start TEXT,
    timestamp_end   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_content_chunks_subject ON content_chunks(subject_id);
CREATE INDEX idx_content_chunks_library_item ON content_chunks(library_item_id);

-- NOTE: vec_chunks virtual table is created at app startup via sqlite-vec extension
-- (dbmate cannot load native extensions, so it must be created in Python)

-- migrate:down

DROP INDEX IF EXISTS idx_content_chunks_library_item;
DROP INDEX IF EXISTS idx_content_chunks_subject;
DROP TABLE IF EXISTS content_chunks;
