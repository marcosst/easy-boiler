import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Request, Response
from fastapi.responses import RedirectResponse

SESSION_COOKIE = "session_token"
SESSION_MAX_AGE_DAYS = 30
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def validate_username(username: str) -> str | None:
    """Return error message or None if valid."""
    if not username or len(username) < 2:
        return "Username deve ter pelo menos 2 caracteres."
    if len(username) > 40:
        return "Username deve ter no máximo 40 caracteres."
    if not USERNAME_PATTERN.match(username):
        return "Username deve conter apenas letras minúsculas, números e hífens, e começar com letra ou número."
    return None


async def create_session(db, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_MAX_AGE_DAYS)
    await db.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires_at.isoformat()),
    )
    await db.commit()
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE_DAYS * 86400,
        httponly=True,
        samesite="lax",
    )


async def get_current_user(request: Request, db) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = await db.execute(
        """SELECT u.id, u.username, u.email
           FROM sessions s JOIN users u ON s.user_id = u.id
           WHERE s.token = ? AND s.expires_at > ?""",
        (token, datetime.now(timezone.utc).isoformat()),
    )
    user = await row.fetchone()
    if not user:
        return None
    return {"id": user["id"], "username": user["username"], "email": user["email"],
            "name": user["username"], "initials": user["username"][:2].upper()}


async def destroy_session(db, token: str) -> None:
    await db.execute("DELETE FROM sessions WHERE token = ?", (token,))
    await db.commit()
