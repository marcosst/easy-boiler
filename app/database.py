import os
import aiosqlite
import sqlite_vec

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")


def get_db_path() -> str:
    url = DATABASE_URL
    if url.startswith("sqlite:////"):
        return url[len("sqlite:///"):]   # keeps leading /
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    if url.startswith("sqlite://"):
        return url[len("sqlite://"):]
    return "/app/data/app.db"


async def _load_vec_extension(db):
    """Load the sqlite-vec extension and ensure vec_chunks table exists."""
    vec_path = sqlite_vec.loadable_path()

    def _load():
        db._conn.enable_load_extension(True)
        db._conn.load_extension(vec_path)
        db._conn.enable_load_extension(False)

    await db._execute(_load)
    await db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
            chunk_id   INTEGER PRIMARY KEY,
            embedding  FLOAT[1536]
        )
    """)
    await db.commit()


async def get_db():
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA busy_timeout = 5000")
        await db.execute("PRAGMA foreign_keys = ON")
        await _load_vec_extension(db)
        db.row_factory = aiosqlite.Row
        yield db
