-- migrate:up
ALTER TABLE library_items ADD COLUMN deleted_at DATETIME DEFAULT NULL;

-- migrate:down
ALTER TABLE library_items DROP COLUMN deleted_at;
