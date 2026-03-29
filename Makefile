.PHONY: setup dev migrate db-new db-rollback docker docker-build docker-down docker-logs

DB_URL := sqlite:///$(CURDIR)/data/app.db

# Primeira vez: cria venv e instala dependências
setup:
	uv sync
	cp -n .env.example .env || true
	mkdir -p data midias

# Roda a app com hot-reload
dev:
	mkdir -p data
	DATABASE_URL=$(DB_URL) dbmate up
	if [ -f .env ]; then set -a && . ./.env && set +a; fi; uv run uvicorn app.main:app --reload --port 8000

# Só roda as migrations
migrate:
	DATABASE_URL=$(DB_URL) dbmate up

# Cria nova migration: make db-new name=create_users
db-new:
	DATABASE_URL=$(DB_URL) dbmate new $(name)

# Desfaz a última migration
db-rollback:
	DATABASE_URL=$(DB_URL) dbmate rollback

# Docker
docker:
	docker compose up

docker-build:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f
