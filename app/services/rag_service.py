"""RAG service: vector search, prompt assembly, and streaming LLM completion."""

import logging
import os
import struct
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.services.embedding_service import generate_embeddings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Você é um assistente que responde perguntas sobre "{subject_name}".
Use APENAS o contexto fornecido abaixo para responder.
Se não souber a resposta com base no contexto, diga que não encontrou informação sobre isso.

Responda em português brasileiro.

O contexto contém trechos de legendas de vídeos com timestamps no formato [HH:MM:SS].

Quando citar informações, inclua links clicáveis para o momento exato do vídeo usando markdown:
[nome_do_video - HH:MM:SS](url_do_video&t=Xs)
Onde X é o timestamp convertido para segundos.

Não ofereça ajuda expontâna, não faça perguntas, apenas responda com base no contexto.

URLs dos vídeos:
{video_urls}

--- Contexto ---
{context}
--- Fim do Contexto ---"""

MAX_DISTANCE = 1.2  # cosine distance threshold — discard chunks above this


async def search_chunks(db, subject_id: int, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Search for the most relevant chunks via sqlite-vec KNN, filtered by subject_id."""
    embedding_bytes = struct.pack(f"{len(query_embedding)}f", *query_embedding)

    # Over-fetch from vec_chunks (virtual table doesn't support WHERE on non-vector cols)
    # Then JOIN + filter by subject_id + distance threshold
    cursor = await db.execute("""
        SELECT cc.id, cc.chunk_text, cc.timestamp_start, cc.timestamp_end,
               cc.library_item_id, li.name AS video_name, li.url AS video_url,
               v.distance
        FROM (
            SELECT chunk_id, distance
            FROM vec_chunks
            WHERE embedding MATCH ? AND k = ?
        ) v
        JOIN content_chunks cc ON cc.id = v.chunk_id
        JOIN library_items li ON li.id = cc.library_item_id
        WHERE cc.subject_id = ?
          AND v.distance <= ?
        ORDER BY v.distance
        LIMIT ?
    """, (embedding_bytes, top_k * 4, subject_id, MAX_DISTANCE, top_k))

    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


def _format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks — includes full subtitle lines with timestamps."""
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"=== Vídeo: {c['video_name']} ===\n{c['chunk_text']}")
    return "\n\n".join(parts)


def _format_video_urls(chunks: list[dict]) -> str:
    """List video names and their base URLs for the LLM to build links."""
    seen = {}
    for c in chunks:
        name = c.get("video_name", "")
        url = c.get("video_url", "")
        if name and url and name not in seen:
            seen[name] = url
    return "\n".join(f'- "{name}": {url}' for name, url in seen.items())



def build_chat_messages(
    subject_name: str, chunks: list[dict], question: str, history: list[dict]
) -> list[dict]:
    """Assemble the full message list for the LLM."""
    context = _format_context(chunks)
    video_urls = _format_video_urls(chunks)
    system = SYSTEM_PROMPT_TEMPLATE.format(
        subject_name=subject_name, context=context, video_urls=video_urls
    )

    messages = [{"role": "system", "content": system}]

    # Add conversation history (last 5 exchanges)
    for msg in history[-10:]:
        role = msg.get("role", "user")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": msg.get("text", "")})

    messages.append({"role": "user", "content": question})
    return messages


async def stream_completion(messages: list[dict]) -> AsyncIterator[str]:
    """Stream tokens from OpenAI chat completion."""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    stream = await client.chat.completions.create(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-nano"),
        #gpt-4o-mini
        messages=messages,
        temperature=0.4,
        stream=True,
    )
    async for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta
