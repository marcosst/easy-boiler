-- migrate:up
ALTER TABLE projects ADD COLUMN content_md TEXT;

CREATE TABLE library_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('video', 'pdf', 'document', 'other')),
    url TEXT,
    file_path TEXT,
    image_path TEXT,
    subtitle_path TEXT,
    metadata TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_library_items_project ON library_items(project_id);

-- Seed content_md for existing projects
UPDATE projects SET content_md = '# Introdução
## Visão Geral
### Resumo do tema
Este é um conteúdo de exemplo em **markdown**.

- Ponto importante 1
- Ponto importante 2
- Ponto importante 3
### Material complementar
## Contexto Histórico
### Linha do tempo
Texto sobre a história do tema.
# Conceitos Fundamentais
## Definições
### Glossário de termos
Lista de termos e definições relevantes.
### Diagrama conceitual
## Princípios
### Princípio 1
Descrição do primeiro princípio fundamental.
# Aplicações Práticas
## Estudo de Caso
### Exemplo resolvido
Passo a passo de um problema resolvido.

Com detalhes adicionais.
### Exercício proposto
## Exercícios
### Exercício 1
Resolva o problema aplicando os conceitos aprendidos.'
WHERE content_md IS NULL;

-- migrate:down
DROP INDEX IF EXISTS idx_library_items_project;
DROP TABLE IF EXISTS library_items;

-- SQLite does not support DROP COLUMN before 3.35.0; recreate table if needed.
-- For simplicity, just leave the column (it will be ignored).
