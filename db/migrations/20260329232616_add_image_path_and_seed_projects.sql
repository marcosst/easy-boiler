-- migrate:up
ALTER TABLE projects ADD COLUMN image_path TEXT;

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Reforma Apartamento 302', 'reforma-apartamento-302', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Orcamento Obra Centro', 'orcamento-obra-centro', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Residencial Vila Nova', 'residencial-vila-nova', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Projeto Fachada Comercial', 'projeto-fachada-comercial', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

INSERT INTO projects (name, shortname, is_public, owner_id)
SELECT 'Levantamento Terreno Sul', 'levantamento-terreno-sul', 0, u.id
FROM users u WHERE u.email = 'marcos@medire.com.br';

-- migrate:down
DELETE FROM projects WHERE shortname IN (
    'reforma-apartamento-302',
    'orcamento-obra-centro',
    'residencial-vila-nova',
    'projeto-fachada-comercial',
    'levantamento-terreno-sul'
);

-- SQLite 3.35+ supports ALTER TABLE DROP COLUMN
ALTER TABLE projects DROP COLUMN image_path;
