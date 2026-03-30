-- migrate:up
ALTER TABLE users DROP COLUMN language;

-- migrate:down
ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'pt';
