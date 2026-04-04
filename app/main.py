import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import fitz  # pymupdf

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    SESSION_COOKIE,
    create_session,
    destroy_session,
    get_current_user,
    get_optional_user,
    hash_password,
    oauth,
    PROVIDERS,
    set_session_cookie,
    validate_username,
    verify_password,
)
from app.database import get_db
from app.queue import get_queue_db, enqueue
from app.services.apify_service import fetch_apify_data, fetch_playlist_videos

import logging
from app.services.file_service import (
    ImageValidationError,
    MAX_IMAGE_SIZE,
    SHORTNAME_RE,
    SHORTNAME_MIN,
    SHORTNAME_MAX,
    save_upload_image,
)
from app.services.llm_classifier import classify_transcript
from app.services.taxonomy_service import get_taxonomy_for_subject
from app.services.tree_builder import rebuild_content_json
from app.services.url_builder import build_step_url

app = FastAPI()

logger = logging.getLogger(__name__)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/midias", StaticFiles(directory="midias"), name="midias")
templates = Jinja2Templates(directory="app/templates")

# Global UI tokens — change here to update all components consistently
BTN_H = "h-10"
BTN_WH = "w-10 h-10"
INPUT_CLS = (
    "w-full px-3.5 py-2.5 bg-white dark:bg-neutral-800 border border-slate-200"
    " dark:border-neutral-700 rounded-lg text-slate-700 dark:text-neutral-300 text-sm"
    " placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2"
    " focus:ring-teal-500/50 focus:border-teal-500 transition-colors"
)
INPUT_CLS_ERR = (
    "w-full px-3.5 py-2.5 bg-white dark:bg-neutral-800 border border-red-400"
    " dark:border-red-500 rounded-lg text-slate-700 dark:text-neutral-300 text-sm"
    " placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2"
    " focus:ring-red-500/50 focus:border-red-500 transition-colors"
)
BTN_PRIMARY = (
    "w-full h-10 rounded-lg bg-brand hover:bg-brand-dark text-white text-sm"
    " font-semibold transition-colors cursor-pointer disabled:opacity-50"
    " disabled:cursor-not-allowed"
)
LABEL_CLS = (
    "block text-xs font-semibold text-slate-500 dark:text-neutral-400"
    " uppercase tracking-wider mb-1.5"
)
templates.env.globals["BTN_H"] = BTN_H
templates.env.globals["BTN_WH"] = BTN_WH
templates.env.globals["INPUT_CLS"] = INPUT_CLS
templates.env.globals["INPUT_CLS_ERR"] = INPUT_CLS_ERR
templates.env.globals["BTN_PRIMARY"] = BTN_PRIMARY
templates.env.globals["LABEL_CLS"] = LABEL_CLS


@app.get("/health")
async def health():
    return {"status": "ok"}


def _ctx(request: Request, context: dict | None = None) -> dict:
    ctx = context or {}
    return ctx


def parse_topics_json(content_json: str | None) -> list:
    """Parse JSON content into a list of topics."""
    if not content_json:
        return []
    data = json.loads(content_json)
    return data.get("topicos", [])


async def _extract_error_msg(item_id: int, metadata_str: str | None) -> str:
    """Extract error message from metadata JSON, falling back to queue.db."""
    error_msg = ""
    if metadata_str:
        try:
            meta = json.loads(metadata_str)
            error_msg = meta.get("error_msg", "")
        except (json.JSONDecodeError, TypeError):
            pass
    if not error_msg:
        try:
            async with get_queue_db() as queue_db:
                qrow = await queue_db.execute(
                    "SELECT error_msg FROM jobs WHERE library_item_id = ? AND status = 'error' ORDER BY finished_at DESC LIMIT 1",
                    (item_id,),
                )
                job_row = await qrow.fetchone()
                if job_row and job_row["error_msg"]:
                    error_msg = job_row["error_msg"]
        except Exception:
            pass
    return error_msg


# --- Auth redirect exception ---

class AuthRedirect(Exception):
    pass


@app.exception_handler(AuthRedirect)
async def auth_redirect_handler(request: Request, exc: AuthRedirect):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={"request": request},
        status_code=404,
    )


async def require_auth(request: Request, db=Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise AuthRedirect()
    return user


# --- Public auth routes ---

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context=_ctx(request))


@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db),
):
    row = await db.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
    user = await row.fetchone()
    if not user or not user["password_hash"] or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request=request, name="login.html",
            context=_ctx(request, {"error": "Email ou senha incorretos."}),
            status_code=422,
        )
    token = await create_session(db, user["id"])
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, token)
    return response


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context=_ctx(request))


@app.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db=Depends(get_db),
):
    username = username.strip().lower()
    err = validate_username(username)
    if err:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context=_ctx(request, {"error": err, "username": username, "email": email}),
            status_code=422,
        )
    if password != password_confirm:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context=_ctx(request, {"error": "As senhas não coincidem.", "username": username, "email": email}),
            status_code=422,
        )
    row = await db.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
    if await row.fetchone():
        return templates.TemplateResponse(
            request=request, name="register.html",
            context=_ctx(request, {"error": "Email ou username já em uso.", "username": username, "email": email}),
            status_code=422,
        )
    cursor = await db.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, hash_password(password)),
    )
    await db.commit()
    token = await create_session(db, cursor.lastrowid)
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, token)
    return response


@app.get("/logout")
async def logout(request: Request, db=Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await destroy_session(db, token)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


# --- OAuth routes ---

@app.get("/auth/choose-username")
async def choose_username_page(request: Request):
    if "oauth_email" not in request.session:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request=request, name="choose_username.html", context=_ctx(request))


@app.post("/auth/choose-username")
async def choose_username_submit(
    request: Request,
    username: str = Form(...),
    db=Depends(get_db),
):
    if "oauth_email" not in request.session:
        return RedirectResponse("/login", status_code=303)

    username = username.strip().lower()
    err = validate_username(username)
    if err:
        return templates.TemplateResponse(
            request=request, name="choose_username.html",
            context=_ctx(request, {"error": err, "username": username}),
            status_code=422,
        )

    row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if await row.fetchone():
        return templates.TemplateResponse(
            request=request, name="choose_username.html",
            context=_ctx(request, {"error": "Username já em uso.", "username": username}),
            status_code=422,
        )

    email = request.session["oauth_email"]
    provider = request.session["oauth_provider"]
    provider_user_id = request.session["oauth_provider_user_id"]

    cursor = await db.execute(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        (username, email),
    )
    user_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO oauth_accounts (user_id, provider, provider_user_id) VALUES (?, ?, ?)",
        (user_id, provider, provider_user_id),
    )
    await db.commit()

    request.session.pop("oauth_email", None)
    request.session.pop("oauth_provider", None)
    request.session.pop("oauth_provider_user_id", None)

    token = await create_session(db, user_id)
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, token)
    return response


@app.get("/auth/{provider}")
async def oauth_login(request: Request, provider: str):
    client = PROVIDERS.get(provider)
    if not client:
        raise HTTPException(status_code=404, detail="Provider não configurado")
    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await client.authorize_redirect(request, str(redirect_uri))


@app.get("/auth/{provider}/callback")
async def oauth_callback(request: Request, provider: str, db=Depends(get_db)):
    client = PROVIDERS.get(provider)
    if not client:
        raise HTTPException(status_code=404, detail="Provider não configurado")

    token_data = await client.authorize_access_token(request)

    if provider == "github":
        resp = await client.get("user", token=token_data)
        profile = resp.json()
        provider_user_id = str(profile["id"])
        email = profile.get("email")
        if not email:
            email_resp = await client.get("user/emails", token=token_data)
            emails = email_resp.json()
            primary = next((e for e in emails if e["primary"]), None)
            email = primary["email"] if primary else None
    else:
        userinfo = token_data.get("userinfo", {})
        provider_user_id = userinfo.get("sub", "")
        email = userinfo.get("email")

    if not email:
        return templates.TemplateResponse(
            request=request, name="login.html",
            context=_ctx(request, {"error": "Não foi possível obter o email do provedor."}),
            status_code=422,
        )

    row = await db.execute(
        "SELECT user_id FROM oauth_accounts WHERE provider = ? AND provider_user_id = ?",
        (provider, provider_user_id),
    )
    existing_oauth = await row.fetchone()

    if existing_oauth:
        token = await create_session(db, existing_oauth["user_id"])
        response = RedirectResponse("/", status_code=303)
        set_session_cookie(response, token)
        return response

    row = await db.execute("SELECT id FROM users WHERE email = ?", (email,))
    existing_user = await row.fetchone()

    if existing_user:
        await db.execute(
            "INSERT INTO oauth_accounts (user_id, provider, provider_user_id) VALUES (?, ?, ?)",
            (existing_user["id"], provider, provider_user_id),
        )
        await db.commit()
        token = await create_session(db, existing_user["id"])
        response = RedirectResponse("/", status_code=303)
        set_session_cookie(response, token)
        return response

    request.session["oauth_email"] = email
    request.session["oauth_provider"] = provider
    request.session["oauth_provider_user_id"] = provider_user_id
    return RedirectResponse("/auth/choose-username", status_code=303)


# --- Public data routes (must be before catch-all /{username}) ---

@app.get("/htmx/search")
async def htmx_search(request: Request, q: str = "", db=Depends(get_db)):
    q = q.strip()
    if q:
        cursor = await db.execute(
            """SELECT s.id, s.name, s.shortname, s.image_path, u.username
               FROM subjects s JOIN users u ON s.owner_id = u.id
               WHERE s.is_public = 1 AND s.name LIKE ?
               ORDER BY s.created_at DESC
               LIMIT 50""",
            (f"%{q}%",),
        )
    else:
        cursor = await db.execute(
            """SELECT s.id, s.name, s.shortname, s.image_path, u.username
               FROM subjects s JOIN users u ON s.owner_id = u.id
               WHERE s.is_public = 1
               ORDER BY s.created_at DESC
               LIMIT 50""",
        )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="partials/subject_cards.html",
        context={"subjects": subjects},
    )


@app.get("/busca")
async def busca(request: Request, q: str = "", db=Depends(get_db)):
    q = q.strip()
    if q:
        cursor = await db.execute(
            """SELECT s.id, s.name, s.shortname, s.image_path, u.username
               FROM subjects s JOIN users u ON s.owner_id = u.id
               WHERE s.is_public = 1 AND s.name LIKE ?
               ORDER BY s.created_at DESC
               LIMIT 50""",
            (f"%{q}%",),
        )
    else:
        cursor = await db.execute(
            """SELECT s.id, s.name, s.shortname, s.image_path, u.username
               FROM subjects s JOIN users u ON s.owner_id = u.id
               WHERE s.is_public = 1
               ORDER BY s.created_at DESC
               LIMIT 50""",
        )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="busca.html",
        context={"subjects": subjects, "q": q},
    )


@app.get("/")
async def home(request: Request, db=Depends(get_db)):
    user = await get_optional_user(request, db)
    if user:
        return RedirectResponse(f"/{user['username']}", status_code=303)
    cursor = await db.execute(
        """SELECT s.id, s.name, s.shortname, s.image_path, u.username
           FROM subjects s JOIN users u ON s.owner_id = u.id
           WHERE s.is_public = 1
           ORDER BY s.created_at DESC
           LIMIT 50""",
    )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"subjects": subjects},
    )


@app.get("/{username}")
async def user_subjects(request: Request, username: str, db=Depends(get_db)):
    user = await get_optional_user(request, db)
    row = await db.execute("SELECT id, username FROM users WHERE username = ?", (username,))
    profile_user = await row.fetchone()
    if not profile_user:
        raise HTTPException(status_code=404)
    is_owner = user is not None and user["id"] == profile_user["id"]
    if is_owner:
        cursor = await db.execute(
            "SELECT id, name, shortname, image_path, is_public, created_at FROM subjects WHERE owner_id = ? ORDER BY created_at DESC",
            (profile_user["id"],),
        )
    else:
        cursor = await db.execute(
            "SELECT id, name, shortname, image_path, is_public, created_at FROM subjects WHERE owner_id = ? AND is_public = 1 ORDER BY created_at DESC",
            (profile_user["id"],),
        )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=_ctx(request, {
            "user": user,
            "is_owner": is_owner,
            "profile_username": profile_user["username"],
            "subjects": subjects,
            "shortname_pattern": SHORTNAME_RE.pattern,
            "shortname_min": SHORTNAME_MIN,
            "shortname_max": SHORTNAME_MAX,
            "max_image_size": MAX_IMAGE_SIZE,
        }),
    )


@app.post("/htmx/subjects")
async def htmx_create_subject(
    request: Request,
    name: str = Form(...),
    shortname: str = Form(...),
    is_public: bool = Form(False),
    image: UploadFile | None = File(None),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    name = name.strip()
    shortname = shortname.strip().lower()

    if not name:
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "name", "message": "Informe o título do assunto."}}'},
        )

    if len(shortname) < SHORTNAME_MIN or len(shortname) > SHORTNAME_MAX or not SHORTNAME_RE.match(shortname):
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "shortname", "message": "Apenas letras minúsculas, números e hífens (mín. 2, máx. 64 caracteres)."}}'},
        )

    row = await db.execute("SELECT id FROM subjects WHERE shortname = ?", (shortname,))
    if await row.fetchone():
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "shortname", "message": "Este nome curto já está em uso. Escolha outro."}}'},
        )

    image_path = None
    if image and image.filename:
        try:
            image_path = await save_upload_image(image)
        except ImageValidationError as e:
            return Response(
                status_code=422,
                headers={"HX-Trigger": json.dumps({"subject-error": {"field": e.field, "message": e.message}})},
            )

    await db.execute(
        "INSERT INTO subjects (name, shortname, is_public, owner_id, image_path) VALUES (?, ?, ?, ?, ?)",
        (name, shortname, int(is_public), user["id"], image_path),
    )
    await db.commit()

    return Response(
        status_code=204,
        headers={"HX-Redirect": f"/{user['username']}"},
    )


@app.put("/htmx/subjects/{subject_id}")
async def htmx_update_subject(
    request: Request,
    subject_id: int,
    name: str = Form(...),
    shortname: str = Form(...),
    is_public: bool = Form(False),
    image: UploadFile | None = File(None),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    row = await db.execute(
        "SELECT id, shortname, image_path FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)

    name = name.strip()
    shortname = shortname.strip().lower()

    if not name:
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "name", "message": "Informe o título do assunto."}}'},
        )

    if len(shortname) < SHORTNAME_MIN or len(shortname) > SHORTNAME_MAX or not SHORTNAME_RE.match(shortname):
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "shortname", "message": "Apenas letras minúsculas, números e hífens (mín. 2, máx. 64 caracteres)."}}'},
        )

    row = await db.execute(
        "SELECT id FROM subjects WHERE shortname = ? AND id != ?",
        (shortname, subject_id),
    )
    if await row.fetchone():
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "shortname", "message": "Este nome curto já está em uso. Escolha outro."}}'},
        )

    image_path = subject["image_path"]
    if image and image.filename:
        try:
            image_path = await save_upload_image(image, old_filename=subject["image_path"])
        except ImageValidationError as e:
            return Response(
                status_code=422,
                headers={"HX-Trigger": json.dumps({"subject-error": {"field": e.field, "message": e.message}})},
            )

    await db.execute(
        "UPDATE subjects SET name = ?, shortname = ?, is_public = ?, image_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (name, shortname, int(is_public), image_path, subject_id),
    )
    await db.commit()

    return Response(
        status_code=204,
        headers={"HX-Redirect": f"/{user['username']}"},
    )


@app.delete("/htmx/subjects/{subject_id}")
async def htmx_delete_subject(
    request: Request,
    subject_id: int,
    user=Depends(require_auth),
    db=Depends(get_db),
):
    form = await request.form()
    shortname_confirm = form.get("shortname_confirm", "").strip()

    row = await db.execute(
        "SELECT id, shortname, image_path FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)

    if shortname_confirm != subject["shortname"]:
        return Response(
            status_code=422,
            headers={"HX-Trigger": '{"subject-error": {"field": "delete", "message": "Nome curto não confere."}}'},
        )

    if subject["image_path"]:
        old_path = Path("midias") / subject["image_path"]
        old_path.unlink(missing_ok=True)

    await db.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    await db.commit()

    return Response(
        status_code=204,
        headers={"HX-Redirect": f"/{user['username']}"},
    )


@app.get("/{username}/{shortname}")
async def subject_topics(request: Request, username: str, shortname: str, db=Depends(get_db)):
    user = await get_optional_user(request, db)
    row = await db.execute(
        """
        SELECT s.id, s.name, s.shortname, s.content_json, s.image_path, s.is_public, u.id AS owner_id
        FROM subjects s
        JOIN users u ON s.owner_id = u.id
        WHERE u.username = ? AND s.shortname = ?
        """,
        (username, shortname),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    # Determine ownership
    is_owner = user is not None and user["id"] == subject["owner_id"]
    # Private subjects are only visible to the owner
    if not subject["is_public"] and not is_owner:
        raise HTTPException(status_code=404)
    topics = parse_topics_json(subject["content_json"])
    cursor = await db.execute(
        """
        SELECT id, name, type, url, file_path, image_path, status, metadata
        FROM library_items
        WHERE subject_id = ? AND deleted_at IS NULL
        ORDER BY position
        """,
        (subject["id"],),
    )
    library_items = [dict(row) for row in await cursor.fetchall()]
    for item in library_items:
        if item["type"] == "youtube" and item["url"]:
            m = YOUTUBE_RE.search(item["url"])
            if m:
                item["thumbnail_url"] = f"https://img.youtube.com/vi/{m.group(1)}/mqdefault.jpg"
            else:
                item["thumbnail_url"] = None
        else:
            item["thumbnail_url"] = None
        # Extract error_msg for error items
        if item.get("status") == "error":
            item["error_msg"] = await _extract_error_msg(item["id"], item.get("metadata"))
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context=_ctx(request, {
            "user": user,
            "is_owner": is_owner,
            "subject": subject,
            "topics": topics,
            "username": username,
            "shortname": shortname,
            "library_items": library_items,
        }),
    )


YOUTUBE_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)"
)


def _extract_playlist_id(url: str) -> str | None:
    """Return the playlist ID from a YouTube URL, or None."""
    parsed = urlparse(url)
    list_ids = parse_qs(parsed.query).get("list", [])
    return list_ids[0] if list_ids else None


def _video_id_from_url(url: str) -> str | None:
    """Extract YouTube video_id from a URL, or None."""
    m = YOUTUBE_RE.search(url)
    return m.group(1) if m else None


async def _get_existing_video_ids(db, subject_id: int) -> set[str]:
    """Return set of YouTube video_ids already in the subject's library."""
    rows = await db.execute_fetchall(
        "SELECT url FROM library_items WHERE subject_id = ? AND type = 'youtube' AND deleted_at IS NULL",
        (subject_id,),
    )
    existing = set()
    for row in rows:
        m = YOUTUBE_RE.search(row["url"] or "")
        if m:
            existing.add(m.group(1))
    return existing


MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB



@app.post("/htmx/library/preview")
async def htmx_library_preview(
    request: Request,
    type: str = Form(...),
    subject_id: int = Form(...),
    url: str | None = Form(None),
    file: UploadFile | None = File(None),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    # Verify subject belongs to user
    row = await db.execute(
        "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404)

    username = user["username"]
    thumb_dir = Path("midias") / username / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    if type == "youtube":
        if not url:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Informe a URL do vídeo."}),
            )

        playlist_id = _extract_playlist_id(url)

        # Playlist-only URL (no video): go straight to playlist video list
        m = YOUTUBE_RE.search(url)
        if not m and playlist_id:
            try:
                videos = await fetch_playlist_videos(url)
            except (ValueError, RuntimeError) as exc:
                return templates.TemplateResponse(
                    request=request,
                    name="partials/library_preview.html",
                    context=_ctx(request, {"error": str(exc)}),
                )
            existing_ids = await _get_existing_video_ids(db, subject_id)
            for v in videos:
                v["existing"] = v["video_id"] in existing_ids
            new_count = sum(1 for v in videos if not v["existing"])
            return templates.TemplateResponse(
                request=request,
                name="partials/library_playlist_videos.html",
                context=_ctx(request, {
                    "videos": videos,
                    "subject_id": subject_id,
                    "playlist_url": url,
                    "new_count": new_count,
                    "total_count": len(videos),
                    "playlist_only": True,
                }),
            )

        if not m:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "URL do YouTube inválida."}),
            )
        video_id = m.group(1)

        # Check if video already exists in user's library
        dup = await db.execute(
            "SELECT id FROM library_items WHERE url = ? AND subject_id = ? AND deleted_at IS NULL",
            (url, subject_id),
        )
        video_already_exists = bool(await dup.fetchone())
        if video_already_exists and not playlist_id:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Este vídeo já existe na biblioteca."}),
            )

        # Fetch title via oEmbed
        title = None
        try:
            oembed_resp = httpx.get(
                "https://noembed.com/embed",
                params={"url": f"https://www.youtube.com/watch?v={video_id}"},
                timeout=10,
            )
            oembed_resp.raise_for_status()
            title = oembed_resp.json().get("title")
        except Exception:
            pass

        if not title:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Não foi possível encontrar este vídeo no YouTube."}),
            )

        # Download thumbnail
        thumb_filename = f"{uuid.uuid4().hex}.jpg"
        thumb_path = thumb_dir / thumb_filename
        try:
            thumb_resp = httpx.get(
                f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                timeout=10,
            )
            thumb_resp.raise_for_status()
            thumb_path.write_bytes(thumb_resp.content)
        except Exception:
            thumb_path = None

        image_path = f"{username}/thumbnails/{thumb_filename}" if thumb_path else None

        return templates.TemplateResponse(
            request=request,
            name="partials/library_preview.html",
            context=_ctx(request, {
                "preview_type": "youtube",
                "preview_name": title,
                "preview_url": url,
                "preview_image_path": image_path,
                "subject_id": subject_id,
                "is_playlist": bool(playlist_id),
                "playlist_url": url if playlist_id else None,
                "video_already_exists": video_already_exists if playlist_id else False,
            }),
        )

    elif type == "pdf":
        if not file or not file.filename:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Selecione um arquivo PDF."}),
            )

        contents = await file.read()
        if len(contents) > MAX_PDF_SIZE:
            return templates.TemplateResponse(
                request=request,
                name="partials/library_preview.html",
                context=_ctx(request, {"error": "Arquivo muito grande (máx. 50MB)."}),
            )

        # Save PDF
        pdf_dir = Path("midias") / username / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_filename = f"{uuid.uuid4().hex}.pdf"
        pdf_path = pdf_dir / pdf_filename
        pdf_path.write_bytes(contents)

        # Generate thumbnail from first page
        thumb_filename = f"{uuid.uuid4().hex}.jpg"
        thumb_path = thumb_dir / thumb_filename
        try:
            doc = fitz.open(stream=contents, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(600 / page.rect.width, 600 / page.rect.width))
            pix.save(str(thumb_path))
            doc.close()
        except Exception:
            thumb_path = None

        image_path = f"{username}/thumbnails/{thumb_filename}" if thumb_path else None
        original_name = Path(file.filename).stem

        return templates.TemplateResponse(
            request=request,
            name="partials/library_preview.html",
            context=_ctx(request, {
                "preview_type": "pdf",
                "preview_name": original_name,
                "preview_file_path": f"{username}/pdfs/{pdf_filename}",
                "preview_image_path": image_path,
                "subject_id": subject_id,
            }),
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/library_preview.html",
        context=_ctx(request, {"error": "Tipo inválido."}),
    )


@app.post("/htmx/library/playlist-videos")
async def htmx_library_playlist_videos(
    request: Request,
    url: str = Form(...),
    subject_id: int = Form(...),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    # Verify subject belongs to user
    row = await db.execute(
        "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404)

    try:
        videos = await fetch_playlist_videos(url)
    except (ValueError, RuntimeError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="partials/library_preview.html",
            context=_ctx(request, {"error": str(exc)}),
        )

    existing_ids = await _get_existing_video_ids(db, subject_id)
    for v in videos:
        v["existing"] = v["video_id"] in existing_ids
    new_count = sum(1 for v in videos if not v["existing"])

    return templates.TemplateResponse(
        request=request,
        name="partials/library_playlist_videos.html",
        context=_ctx(request, {
            "videos": videos,
            "subject_id": subject_id,
            "playlist_url": url,
            "new_count": new_count,
            "total_count": len(videos),
            "playlist_only": False,
        }),
    )


@app.delete("/htmx/library/{item_id}")
async def htmx_library_delete(item_id: int, request: Request, user=Depends(require_auth), db=Depends(get_db)):
    await db.execute(
        """UPDATE library_items SET deleted_at = CURRENT_TIMESTAMP
           WHERE id = ? AND subject_id IN (
               SELECT id FROM subjects WHERE owner_id = ?
           )""",
        (item_id, user["id"]),
    )
    await db.commit()
    # Remove pending/queued jobs from queue
    async with get_queue_db() as queue_db:
        await queue_db.execute(
            "DELETE FROM jobs WHERE library_item_id = ? AND status IN ('queued', 'running')",
            (item_id,),
        )
        await queue_db.commit()
    return Response(status_code=200)


@app.post("/htmx/library/save")
async def htmx_library_save(
    request: Request,
    subject_id: int = Form(...),
    type: str = Form(...),
    name: str = Form(...),
    url: str | None = Form(None),
    file_path: str | None = Form(None),
    image_path: str | None = Form(None),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    name = name.strip()
    if not name:
        return Response(status_code=422, content="Nome é obrigatório.")

    # Verify subject belongs to user
    row = await db.execute(
        "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404)

    username = user["username"]

    # For YouTube, extract video_id for thumbnail URL
    video_id = None
    if type == "youtube" and url:
        m = YOUTUBE_RE.search(url)
        video_id = m.group(1) if m else None

    # PDFs are ready immediately, YouTube items need background processing
    status = "ready" if type != "youtube" else "pending"

    # Get next position
    row = await db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM library_items WHERE subject_id = ?",
        (subject_id,),
    )
    next_pos = (await row.fetchone())["next_pos"]

    cursor = await db.execute(
        """INSERT INTO library_items (subject_id, name, type, url, file_path, image_path, position, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (subject_id, name, type, url, file_path, image_path, next_pos, status),
    )
    await db.commit()

    item_id = cursor.lastrowid

    # Enqueue background processing for YouTube videos
    if type == "youtube":

        async with get_queue_db() as queue_db:
            await enqueue(queue_db, item_id)

    # Build the item dict for the template
    item = {
        "id": item_id,
        "name": name,
        "type": type,
        "url": url,
        "file_path": file_path,
        "image_path": image_path,
        "status": status,
    }
    if type == "youtube" and url and video_id:
        item["thumbnail_url"] = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    else:
        item["thumbnail_url"] = None

    response = templates.TemplateResponse(
        request=request,
        name="partials/library_item.html",
        context=_ctx(request, {"item": item, "is_owner": True}),
    )
    response.headers["HX-Trigger-After-Settle"] = json.dumps({"close-add-modal": True})
    return response


@app.post("/htmx/library/save-playlist")
async def htmx_library_save_playlist(
    request: Request,
    subject_id: int = Form(...),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    form = await request.form()
    raw_videos = form.getlist("videos[]")

    if not raw_videos:
        return Response(status_code=422, content="Nenhum vídeo selecionado.")

    videos = []
    for raw in raw_videos:
        try:
            video = json.loads(raw)
            videos.append(video)
        except (json.JSONDecodeError, TypeError):
            continue

    if not videos:
        return Response(status_code=422, content="Nenhum vídeo selecionado.")

    # Verify subject belongs to user
    row = await db.execute(
        "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404)

    username = user["username"]

    # Filter out videos already in library
    existing_ids = await _get_existing_video_ids(db, subject_id)
    videos = [v for v in videos if _video_id_from_url(v.get("url", "")) not in existing_ids]

    if not videos:
        return Response(status_code=422, content="Todos os vídeos selecionados já estão na biblioteca.")

    # Get next position
    row = await db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM library_items WHERE subject_id = ?",
        (subject_id,),
    )
    next_pos = (await row.fetchone())["next_pos"]

    items_html = []
    item_ids = []
    for i, video in enumerate(videos):
        url = video.get("url", "")
        name = (video.get("title") or f"Vídeo {i + 1}").strip()

        # Extract video_id for thumbnail URL (no download — use YouTube CDN directly)
        m = YOUTUBE_RE.search(url)
        video_id = m.group(1) if m else None

        cursor = await db.execute(
            """INSERT INTO library_items (subject_id, name, type, url, file_path, image_path, position, status)
               VALUES (?, ?, 'youtube', ?, NULL, NULL, ?, 'pending')""",
            (subject_id, name, url, next_pos + i),
        )
        item_id = cursor.lastrowid
        item_ids.append(item_id)

        item = {
            "id": item_id,
            "name": name,
            "type": "youtube",
            "url": url,
            "file_path": None,
            "image_path": None,
            "status": "pending",
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg" if video_id else None,
        }
        item_resp = templates.TemplateResponse(
            request=request,
            name="partials/library_item.html",
            context=_ctx(request, {"item": item, "is_owner": True}),
        )
        items_html.append(item_resp.body.decode())

    await db.commit()

    # Batch enqueue all items
    async with get_queue_db() as queue_db:
        for item_id in item_ids:
            await enqueue(queue_db, item_id)

    response = Response(
        content="".join(items_html),
        media_type="text/html",
    )
    response.headers["HX-Trigger-After-Settle"] = json.dumps({"close-add-modal": True})
    return response


@app.post("/htmx/library/{item_id}/classify")
async def htmx_library_classify(
    item_id: int,
    request: Request,
    user=Depends(require_auth),
    db=Depends(get_db),
):
    # Fetch the library item and verify ownership
    cursor = await db.execute(
        """
        SELECT li.id, li.subtitle_path, li.subject_id, li.url
        FROM library_items li
        JOIN subjects s ON li.subject_id = s.id
        WHERE li.id = ? AND s.owner_id = ?
        """,
        (item_id, user["id"]),
    )
    item = await cursor.fetchone()
    if not item:
        raise HTTPException(status_code=404)

    subject_id = item["subject_id"]
    subtitle_path = item["subtitle_path"]

    # If no subtitle_path, return current accordion unchanged
    if not subtitle_path:
        row = await db.execute("SELECT content_json FROM subjects WHERE id = ?", (subject_id,))
        subject_row = await row.fetchone()
        topics = parse_topics_json(subject_row["content_json"] if subject_row else None)
        return templates.TemplateResponse(
            request=request,
            name="partials/topics_accordion.html",
            context=_ctx(request, {"topics": topics}),
        )

    # Read the subtitle file
    subs_file = Path("midias") / subtitle_path
    if not subs_file.exists():
        logger.error("Subtitle file not found: %s", subs_file)
        row = await db.execute("SELECT content_json FROM subjects WHERE id = ?", (subject_id,))
        subject_row = await row.fetchone()
        topics = parse_topics_json(subject_row["content_json"] if subject_row else None)
        return templates.TemplateResponse(
            request=request,
            name="partials/topics_accordion.html",
            context=_ctx(request, {"topics": topics}),
        )

    transcript = subs_file.read_text(encoding="utf-8").strip()

    # Get existing taxonomy for this subject
    taxonomy = await get_taxonomy_for_subject(db, subject_id)

    result = await classify_transcript(taxonomy, transcript)

    if result is not None:
        # Extract youtube_id from URL
        video_url = item["url"] or ""
        m = YOUTUBE_RE.search(video_url)
        youtube_id = m.group(1) if m else ""

        # Delete old knowledge_items for this library_id (for reprocessing)
        await db.execute("DELETE FROM knowledge_items WHERE library_id = ?", (item_id,))

        # Insert new knowledge_items
        for ki in result.itens:
            url = build_step_url(youtube_id, ki.timestamp) if youtube_id else None
            await db.execute(
                """INSERT INTO knowledge_items
                   (library_id, topico, subtopico, acao, timestamp, pagina, trecho_referencia, file_path, url)
                   VALUES (?, ?, ?, ?, ?, NULL, '', NULL, ?)""",
                (item_id, ki.topico, ki.subtopico, ki.detalhe, ki.timestamp, url),
            )

        # Mark as processed
        await db.execute(
            "UPDATE library_items SET processed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (item_id,),
        )

        # Rebuild the content_json for the subject
        await rebuild_content_json(db, subject_id)
    else:
        logger.warning("LLM classification failed for library_item %d", item_id)

    # Return updated accordion
    row = await db.execute("SELECT content_json FROM subjects WHERE id = ?", (subject_id,))
    subject_row = await row.fetchone()
    topics = parse_topics_json(subject_row["content_json"] if subject_row else None)

    return templates.TemplateResponse(
        request=request,
        name="partials/topics_accordion.html",
        context=_ctx(request, {"topics": topics}),
    )


@app.get("/htmx/library/{item_id}/status")
async def htmx_library_status(item_id: int, request: Request, user=Depends(require_auth), db=Depends(get_db)):
    """Return updated card HTML for polling. Used by items in processing state."""
    cursor = await db.execute(
        """SELECT li.* FROM library_items li
           JOIN subjects s ON li.subject_id = s.id
           WHERE li.id = ? AND s.owner_id = ? AND li.deleted_at IS NULL""",
        (item_id, user["id"]),
    )
    item = await cursor.fetchone()
    if not item:
        raise HTTPException(status_code=404)

    item_dict = dict(item)
    # Add thumbnail_url for YouTube items
    if item_dict.get("type") == "youtube" and item_dict.get("url"):
        m = YOUTUBE_RE.search(item_dict["url"])
        if m:
            item_dict["thumbnail_url"] = f"https://img.youtube.com/vi/{m.group(1)}/mqdefault.jpg"
        else:
            item_dict["thumbnail_url"] = None
    else:
        item_dict["thumbnail_url"] = None

    # Extract error_msg for template display
    if item_dict.get("status") == "error":
        item_dict["error_msg"] = await _extract_error_msg(item_id, item_dict.get("metadata"))

    response = templates.TemplateResponse(
        request=request,
        name="partials/library_item.html",
        context=_ctx(request, {"item": item_dict, "is_owner": True}),
    )
    # When item transitions to ready, trigger topics refresh
    if item_dict.get("status") == "ready":
        response.headers["HX-Trigger"] = json.dumps({"refresh-topics": True})
    return response


@app.post("/htmx/library/{item_id}/retry")
async def htmx_library_retry(item_id: int, request: Request, user=Depends(require_auth), db=Depends(get_db)):
    """Re-enqueue a failed library item for processing."""
    cursor = await db.execute(
        """SELECT li.* FROM library_items li
           JOIN subjects s ON li.subject_id = s.id
           WHERE li.id = ? AND s.owner_id = ? AND li.status = 'error' AND li.deleted_at IS NULL""",
        (item_id, user["id"]),
    )
    item = await cursor.fetchone()
    if not item:
        raise HTTPException(status_code=404)

    # Reset status and re-enqueue
    await db.execute("UPDATE library_items SET status = 'pending' WHERE id = ?", (item_id,))
    await db.commit()

    from app.queue import get_queue_db, enqueue
    async with get_queue_db() as queue_db:
        await enqueue(queue_db, item_id)

    item_dict = dict(item)
    item_dict["status"] = "pending"
    if item_dict.get("type") == "youtube" and item_dict.get("url"):
        m = YOUTUBE_RE.search(item_dict["url"])
        item_dict["thumbnail_url"] = f"https://img.youtube.com/vi/{m.group(1)}/mqdefault.jpg" if m else None
    else:
        item_dict["thumbnail_url"] = None

    return templates.TemplateResponse(
        request=request,
        name="partials/library_item.html",
        context=_ctx(request, {"item": item_dict, "is_owner": True}),
    )


@app.post("/htmx/library/reclassify-all/{subject_id}")
async def htmx_library_reclassify_all(subject_id: int, request: Request, user=Depends(require_auth), db=Depends(get_db)):
    """Delete all knowledge_items for the subject and re-enqueue all items for LLM classification."""
    # Verify subject belongs to user
    cursor = await db.execute(
        "SELECT id FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404)

    # 1. Delete all knowledge_items for this subject
    await db.execute(
        """DELETE FROM knowledge_items WHERE library_id IN (
               SELECT id FROM library_items WHERE subject_id = ? AND deleted_at IS NULL
           )""",
        (subject_id,),
    )

    # 2. Clear content_json
    await db.execute(
        "UPDATE subjects SET content_json = NULL WHERE id = ?",
        (subject_id,),
    )

    # 3. Find all items in this subject
    cursor = await db.execute(
        """SELECT id, url, type, image_path, name, status, metadata, subtitle_path, position
           FROM library_items
           WHERE subject_id = ? AND deleted_at IS NULL
           ORDER BY position""",
        (subject_id,),
    )
    items = [dict(row) for row in await cursor.fetchall()]

    # 4. Set youtube items to pending and enqueue
    youtube_items = [i for i in items if i["type"] == "youtube"]
    for item in youtube_items:
        await db.execute(
            "UPDATE library_items SET status = 'pending' WHERE id = ?",
            (item["id"],),
        )
        item["status"] = "pending"

    await db.commit()

    async with get_queue_db() as queue_db:
        for item in youtube_items:
            # Items with subtitles only need reclassification; others need full processing
            has_subtitles = bool(item.get("subtitle_path"))
            await enqueue(queue_db, item["id"], classify_only=has_subtitles)

    # 5. Add thumbnail URLs for template rendering
    for item in items:
        if item.get("type") == "youtube" and item.get("url"):
            m = YOUTUBE_RE.search(item["url"])
            item["thumbnail_url"] = f"https://img.youtube.com/vi/{m.group(1)}/mqdefault.jpg" if m else None
        else:
            item["thumbnail_url"] = None

    # Return updated library list + trigger topics refresh
    response = templates.TemplateResponse(
        request=request,
        name="partials/library_list.html",
        context=_ctx(request, {"items": items, "is_owner": True}),
    )
    response.headers["HX-Trigger"] = json.dumps({"refresh-topics": True})
    return response


@app.get("/htmx/subjects/{subject_id}/topics")
async def htmx_subject_topics(subject_id: int, request: Request, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute(
        "SELECT content_json FROM subjects WHERE id = ? AND owner_id = ?",
        (subject_id, user["id"]),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    topics = parse_topics_json(subject["content_json"])
    return templates.TemplateResponse(
        request=request,
        name="partials/topics_accordion.html",
        context=_ctx(request, {"topics": topics}),
    )


# --- Public HTMX routes ---

@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html", context=_ctx(request))


