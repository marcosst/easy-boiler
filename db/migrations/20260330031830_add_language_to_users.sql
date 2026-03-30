-- migrate:up
ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'pt';

-- migrate:down
ALTER TABLE users DROP COLUMN language;

