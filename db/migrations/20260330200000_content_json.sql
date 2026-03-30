-- migrate:up

CREATE TABLE subjects_new (
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

INSERT INTO subjects_new (id, name, shortname, is_public, owner_id, image_path, content_json, created_at, updated_at)
SELECT id, name, shortname, is_public, owner_id, image_path, NULL, created_at, updated_at
FROM subjects;

DROP TABLE subjects;
ALTER TABLE subjects_new RENAME TO subjects;

CREATE INDEX idx_subjects_owner ON subjects(owner_id);

-- migrate:down

CREATE TABLE subjects_old (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    shortname  TEXT    NOT NULL UNIQUE
                       CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public  INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    owner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    image_path TEXT,
    content_md TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO subjects_old (id, name, shortname, is_public, owner_id, image_path, content_md, created_at, updated_at)
SELECT id, name, shortname, is_public, owner_id, image_path, NULL, created_at, updated_at
FROM subjects;

DROP TABLE subjects;
ALTER TABLE subjects_old RENAME TO subjects;

CREATE INDEX idx_subjects_owner ON subjects(owner_id);
