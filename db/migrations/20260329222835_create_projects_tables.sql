-- migrate:up

CREATE TABLE projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    shortname    TEXT    NOT NULL UNIQUE
                         CHECK(length(shortname) >= 2 AND shortname NOT GLOB '*[^a-z0-9-]*'),
    is_public    INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1)),
    owner_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_projects_owner ON projects(owner_id);

CREATE TABLE project_images (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename   TEXT    NOT NULL,
    position   INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_project_images_project ON project_images(project_id);

-- migrate:down

DROP TABLE IF EXISTS project_images;
DROP TABLE IF EXISTS projects;
