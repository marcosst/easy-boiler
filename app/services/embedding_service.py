"""Generate and store OpenAI embeddings for content chunks."""

import logging
import os
import struct

from openai import AsyncOpenAI

from app.services.chunking_service import ChunkResult

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Call OpenAI embeddings API in batch."""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def _pack_embedding(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


async def store_chunks_with_embeddings(
    db, subject_id: int, library_item_id: int, chunks: list[ChunkResult]
) -> int:
    """Generate embeddings and store chunks + vectors. Returns count stored."""
    if not chunks:
        return 0

    texts = [c.embed_text for c in chunks]
    embeddings = await generate_embeddings(texts)

    count = 0
    for chunk, embedding in zip(chunks, embeddings):
        cursor = await db.execute(
            """INSERT INTO content_chunks
               (subject_id, library_item_id, chunk_text, chunk_index, timestamp_start, timestamp_end)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (subject_id, library_item_id, chunk.chunk_text,
             chunk.chunk_index, chunk.timestamp_start, chunk.timestamp_end),
        )
        chunk_id = cursor.lastrowid
        await db.execute(
            "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
            (chunk_id, _pack_embedding(embedding)),
        )
        count += 1

    await db.commit()
    return count


async def delete_chunks_for_item(db, library_item_id: int) -> None:
    """Delete all chunks and their embeddings for a library item."""
    # Delete vec_chunks first (no CASCADE on virtual tables)
    await db.execute(
        "DELETE FROM vec_chunks WHERE chunk_id IN (SELECT id FROM content_chunks WHERE library_item_id = ?)",
        (library_item_id,),
    )
    await db.execute(
        "DELETE FROM content_chunks WHERE library_item_id = ?",
        (library_item_id,),
    )
    await db.commit()
