import os
import aiosqlite

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


async def get_db():
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA busy_timeout = 5000")
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        yield db
