-- migrate:up
ALTER TABLE projects RENAME TO subjects;
ALTER TABLE project_images RENAME TO subject_images;
ALTER TABLE library_items RENAME COLUMN project_id TO subject_id;
ALTER TABLE subject_images RENAME COLUMN project_id TO subject_id;

DROP INDEX IF EXISTS idx_projects_owner;
CREATE INDEX idx_subjects_owner ON subjects(owner_id);

DROP INDEX IF EXISTS idx_project_images_project;
CREATE INDEX idx_subject_images_subject ON subject_images(subject_id);

DROP INDEX IF EXISTS idx_library_items_project;
CREATE INDEX idx_library_items_subject ON library_items(subject_id);

-- migrate:down
DROP INDEX IF EXISTS idx_library_items_subject;
DROP INDEX IF EXISTS idx_subject_images_subject;
DROP INDEX IF EXISTS idx_subjects_owner;

ALTER TABLE library_items RENAME COLUMN subject_id TO project_id;
ALTER TABLE subject_images RENAME COLUMN subject_id TO project_id;
ALTER TABLE subject_images RENAME TO project_images;
ALTER TABLE subjects RENAME TO projects;

CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_project_images_project ON project_images(project_id);
CREATE INDEX idx_library_items_project ON library_items(project_id);
