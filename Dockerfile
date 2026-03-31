FROM python:3.12-slim

# Install dbmate
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL -o /usr/local/bin/dbmate \
        https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64 && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/dbmate && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENV DATABASE_URL=sqlite:////app/data/app.db
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]
