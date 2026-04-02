import os
from contextlib import asynccontextmanager

import aiosqlite

QUEUE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "queue.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_item_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    started_at DATETIME,
    finished_at DATETIME,
    error_msg TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
"""


_schema_initialized = False


@asynccontextmanager
async def get_queue_db():
    """Open a connection to the queue database with WAL mode and busy timeout."""
    global _schema_initialized
    async with aiosqlite.connect(QUEUE_DB_PATH) as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA busy_timeout = 5000")
        db.row_factory = aiosqlite.Row
        if not _schema_initialized:
            await db.executescript(_SCHEMA)
            await db.commit()
            _schema_initialized = True
        yield db


async def enqueue(db: aiosqlite.Connection, library_item_id: int) -> int:
    """Insert a new job with status='queued'. Returns the new job id."""
    cursor = await db.execute(
        "INSERT INTO jobs (library_item_id, status) VALUES (?, 'queued')",
        (library_item_id,),
    )
    await db.commit()
    return cursor.lastrowid


async def dequeue(db: aiosqlite.Connection) -> dict | None:
    """Atomically claim the oldest queued job, marking it as running.

    Returns the job as a dict, or None if the queue is empty.
    """
    # Use a transaction to prevent two workers from claiming the same job.
    async with db.execute("BEGIN IMMEDIATE"):
        pass

    row = await db.execute_fetchall(
        "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1"
    )

    if not row:
        await db.execute("ROLLBACK")
        return None

    job = dict(row[0])
    await db.execute(
        """
        UPDATE jobs
           SET status = 'running',
               attempts = attempts + 1,
               started_at = datetime('now')
         WHERE id = ?
        """,
        (job["id"],),
    )
    await db.commit()

    # Return updated values
    job["status"] = "running"
    job["attempts"] = job["attempts"] + 1
    return job


async def complete(db: aiosqlite.Connection, job_id: int) -> None:
    """Mark a job as done."""
    await db.execute(
        "UPDATE jobs SET status = 'done', finished_at = datetime('now') WHERE id = ?",
        (job_id,),
    )
    await db.commit()


async def fail(db: aiosqlite.Connection, job_id: int, error_msg: str) -> None:
    """Mark a job as error, recording the error message."""
    await db.execute(
        """
        UPDATE jobs
           SET status = 'error',
               finished_at = datetime('now'),
               error_msg = ?
         WHERE id = ?
        """,
        (error_msg, job_id),
    )
    await db.commit()


async def requeue_stale(db: aiosqlite.Connection, timeout_minutes: int = 10) -> None:
    """Reset stale 'running' jobs back to 'queued' for crash recovery.

    A job is considered stale if its started_at is older than timeout_minutes ago.
    """
    # Requeue jobs that haven't exhausted their attempts
    await db.execute(
        """
        UPDATE jobs
           SET status = 'queued',
               started_at = NULL
         WHERE status = 'running'
           AND started_at < datetime('now', ? || ' minutes')
           AND attempts < max_attempts
        """,
        (f"-{timeout_minutes}",),
    )
    # Mark exhausted jobs as error
    await db.execute(
        """
        UPDATE jobs
           SET status = 'error',
               finished_at = datetime('now'),
               error_msg = 'Número máximo de tentativas excedido'
         WHERE status = 'running'
           AND started_at < datetime('now', ? || ' minutes')
           AND attempts >= max_attempts
        """,
        (f"-{timeout_minutes}",),
    )
    await db.commit()
