"""Background worker that processes video library items from the job queue."""

import asyncio
import json
import logging
import re
import os
import sys
from pathlib import Path

import aiosqlite

from app.queue import get_queue_db, dequeue, complete, fail, requeue_stale
from app.services.apify_service import fetch_apify_data
from app.services.llm_classifier import classify_transcript
from app.services.taxonomy_service import get_taxonomy_for_subject
from app.services.tree_builder import rebuild_content_json
from app.services.url_builder import build_step_url

logger = logging.getLogger("worker")

YOUTUBE_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)"
)

# Main app database path
APP_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")

POLL_INTERVAL = 5  # seconds


async def get_app_db():
    """Open a connection to the main app database with WAL mode."""
    db = await aiosqlite.connect(APP_DB_PATH)
    await db.execute("PRAGMA journal_mode = WAL")
    await db.execute("PRAGMA busy_timeout = 5000")
    await db.execute("PRAGMA foreign_keys = ON")
    db.row_factory = aiosqlite.Row
    return db


async def update_item_status(app_db, item_id: int, status: str, error_msg: str = ""):
    """Update library_items.status in the main app database.

    When status is 'error', stores the error message in the metadata JSON field.
    """
    if status == "error" and error_msg:
        # Store error_msg in metadata JSON so the template can display it
        cursor = await app_db.execute(
            "SELECT metadata FROM library_items WHERE id = ?", (item_id,)
        )
        row = await cursor.fetchone()
        metadata = json.loads(row["metadata"]) if row and row["metadata"] else {}
        metadata["error_msg"] = error_msg
        await app_db.execute(
            "UPDATE library_items SET status = ?, metadata = ? WHERE id = ?",
            (status, json.dumps(metadata, ensure_ascii=False), item_id),
        )
    else:
        await app_db.execute(
            "UPDATE library_items SET status = ? WHERE id = ?",
            (status, item_id),
        )
    await app_db.commit()


async def process_job(job: dict, app_db, queue_db) -> None:
    """Process a single job: fetch subtitles via Apify, classify via LLM."""
    item_id = job["library_item_id"]
    job_id = job["id"]

    # Get library item details from app.db
    cursor = await app_db.execute(
        """SELECT li.id, li.url, li.type, li.subject_id, li.subtitle_path, li.deleted_at,
                  s.owner_id, u.username
           FROM library_items li
           JOIN subjects s ON li.subject_id = s.id
           JOIN users u ON s.owner_id = u.id
           WHERE li.id = ?""",
        (item_id,),
    )
    item = await cursor.fetchone()

    if not item or item["deleted_at"] is not None:
        logger.info("Item %d not found or deleted, skipping", item_id)
        await complete(queue_db, job_id)
        return

    if item["type"] != "youtube" or not item["url"]:
        logger.info("Item %d is not a YouTube video, skipping", item_id)
        await update_item_status(app_db, item_id, "ready")
        await complete(queue_db, job_id)
        return

    url = item["url"]
    subject_id = item["subject_id"]
    username = item["username"]

    m = YOUTUBE_RE.search(url)
    video_id = m.group(1) if m else None
    if not video_id:
        await update_item_status(app_db, item_id, "error", "URL do YouTube inválida")
        await fail(queue_db, job_id, "Invalid YouTube URL")
        return

    # --- Step 1: Fetch subtitles via Apify ---
    await update_item_status(app_db, item_id, "fetching")
    logger.info("[%d] Fetching subtitles for %s", item_id, video_id)

    try:
        metadata, subtitle_text = await fetch_apify_data(url)
    except (ValueError, RuntimeError) as exc:
        logger.error("[%d] Apify fetch failed: %s", item_id, exc)
        await update_item_status(app_db, item_id, "error", str(exc))
        await fail(queue_db, job_id, str(exc))
        return

    # Save metadata
    metadata_json = json.dumps(metadata, ensure_ascii=False)

    # Save subtitles to file
    subs_dir = Path("midias") / username / "subtitles"
    subs_dir.mkdir(parents=True, exist_ok=True)
    subs_file = subs_dir / f"{video_id}.txt"
    subs_file.write_text(subtitle_text + "\n", encoding="utf-8")
    subtitle_path = f"{username}/subtitles/{video_id}.txt"

    # Update library item with metadata and subtitle path
    await app_db.execute(
        "UPDATE library_items SET metadata = ?, subtitle_path = ? WHERE id = ?",
        (metadata_json, subtitle_path, item_id),
    )
    await app_db.commit()

    # --- Step 2: Classify via LLM ---
    await update_item_status(app_db, item_id, "classifying")
    logger.info("[%d] Classifying transcript (%d chars)", item_id, len(subtitle_text))

    taxonomy = await get_taxonomy_for_subject(app_db, subject_id)
    result = await classify_transcript(taxonomy, subtitle_text)

    if result is None:
        logger.error("[%d] LLM classification returned None", item_id)
        await update_item_status(app_db, item_id, "error", "Falha na classificação por IA")
        await fail(queue_db, job_id, "LLM classification failed")
        return

    logger.info("[%d] LLM returned %d items", item_id, len(result.itens))

    # Delete old knowledge_items and insert new ones
    await app_db.execute("DELETE FROM knowledge_items WHERE library_id = ?", (item_id,))
    for ki in result.itens:
        step_url = build_step_url(video_id, ki.timestamp) if video_id else None
        await app_db.execute(
            """INSERT INTO knowledge_items
               (library_id, topico, subtopico, acao, timestamp, pagina, trecho_referencia, file_path, url)
               VALUES (?, ?, ?, ?, ?, NULL, '', NULL, ?)""",
            (item_id, ki.topico, ki.subtopico, ki.acao, ki.timestamp, step_url),
        )

    # Mark as ready and processed
    await app_db.execute(
        "UPDATE library_items SET status = 'ready', processed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (item_id,),
    )
    await app_db.commit()

    # Rebuild content_json for the subject
    await rebuild_content_json(app_db, subject_id)

    await complete(queue_db, job_id)
    logger.info("[%d] Done! Processed successfully", item_id)


async def main_loop():
    """Main worker loop: poll queue, process jobs."""
    logger.info("Worker started, polling every %ds", POLL_INTERVAL)

    app_db = await get_app_db()

    try:
        while True:
            async with get_queue_db() as queue_db:
                # Recover stale jobs
                await requeue_stale(queue_db)

                # Try to get a job
                job = await dequeue(queue_db)

            if job is None:
                await asyncio.sleep(POLL_INTERVAL)
                continue

            logger.info("Processing job %d (item %d, attempt %d/%d)",
                        job["id"], job["library_item_id"],
                        job["attempts"], job["max_attempts"])

            try:
                async with get_queue_db() as queue_db:
                    await process_job(job, app_db, queue_db)
            except Exception as exc:
                logger.exception("Unexpected error processing job %d", job["id"])
                async with get_queue_db() as queue_db:
                    await fail(queue_db, job["id"], str(exc))
                # Also mark item as error
                try:
                    await update_item_status(app_db, job["library_item_id"], "error", f"Erro inesperado: {exc}")
                except Exception:
                    pass
    finally:
        await app_db.close()


def main():
    """Entry point for python -m app.worker"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    # Load .env if present
    from dotenv import load_dotenv
    load_dotenv()

    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
