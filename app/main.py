import json
import os
import re
import uuid
from pathlib import Path

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
    hash_password,
    oauth,
    PROVIDERS,
    set_session_cookie,
    validate_username,
    verify_password,
)
from app.database import get_db

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/midias", StaticFiles(directory="midias"), name="midias")
templates = Jinja2Templates(directory="app/templates")

# Global button size tokens — change here to resize all buttons
BTN_H = "h-10"
BTN_WH = "w-10 h-10"
templates.env.globals["BTN_H"] = BTN_H
templates.env.globals["BTN_WH"] = BTN_WH


def _ctx(request: Request, context: dict | None = None) -> dict:
    ctx = context or {}
    return ctx


def parse_topics_json(content_json: str | None) -> list:
    """Parse JSON content into a list of topics."""
    if not content_json:
        return []
    data = json.loads(content_json)
    return data.get("topicos", [])


# --- Auth redirect exception ---

class AuthRedirect(Exception):
    pass


@app.exception_handler(AuthRedirect)
async def auth_redirect_handler(request: Request, exc: AuthRedirect):
    return RedirectResponse("/login", status_code=303)


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


# --- Protected routes ---

@app.get("/")
async def home(request: Request, user=Depends(require_auth)):
    return RedirectResponse(f"/{user['username']}", status_code=303)


@app.get("/{username}")
async def user_subjects(request: Request, username: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    profile_user = await row.fetchone()
    if not profile_user:
        raise HTTPException(status_code=404)
    cursor = await db.execute(
        "SELECT id, name, shortname, image_path, is_public, created_at FROM subjects WHERE owner_id = ? ORDER BY created_at DESC",
        (profile_user["id"],),
    )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=_ctx(request, {"user": user, "subjects": subjects}),
    )


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MIME_TO_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

SHORTNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


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

    if len(shortname) < 2 or len(shortname) > 64 or not SHORTNAME_RE.match(shortname):
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
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                status_code=422,
                headers={"HX-Trigger": '{"subject-error": {"field": "image", "message": "Tipo de arquivo não suportado."}}'},
            )
        contents = await image.read()
        if len(contents) > MAX_IMAGE_SIZE:
            return Response(
                status_code=422,
                headers={"HX-Trigger": '{"subject-error": {"field": "image", "message": "Arquivo muito grande (máx. 5MB)."}}'},
            )
        ext = MIME_TO_EXT[image.content_type]
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = Path("midias") / filename
        filepath.write_bytes(contents)
        image_path = filename

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

    if len(shortname) < 2 or len(shortname) > 64 or not SHORTNAME_RE.match(shortname):
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
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                status_code=422,
                headers={"HX-Trigger": '{"subject-error": {"field": "image", "message": "Tipo de arquivo não suportado."}}'},
            )
        contents = await image.read()
        if len(contents) > MAX_IMAGE_SIZE:
            return Response(
                status_code=422,
                headers={"HX-Trigger": '{"subject-error": {"field": "image", "message": "Arquivo muito grande (máx. 5MB)."}}'},
            )
        # Remove old image if exists
        if subject["image_path"]:
            old_path = Path("midias") / subject["image_path"]
            old_path.unlink(missing_ok=True)
        ext = MIME_TO_EXT[image.content_type]
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = Path("midias") / filename
        filepath.write_bytes(contents)
        image_path = filename

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
async def subject_topics(request: Request, username: str, shortname: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute(
        """
        SELECT s.id, s.name, s.shortname, s.content_json, s.image_path, s.is_public
        FROM subjects s
        JOIN users u ON s.owner_id = u.id
        WHERE u.username = ? AND s.shortname = ?
        """,
        (username, shortname),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    topics = parse_topics_json(subject["content_json"])
    cursor = await db.execute(
        """
        SELECT id, name, type, url, file_path, image_path
        FROM library_items
        WHERE subject_id = ?
        ORDER BY position
        """,
        (subject["id"],),
    )
    library_items = [dict(row) for row in await cursor.fetchall()]
    for item in library_items:
        if item["type"] == "video" and item["url"]:
            m = YOUTUBE_RE.search(item["url"])
            if m:
                item["thumbnail_url"] = f"https://img.youtube.com/vi/{m.group(1)}/mqdefault.jpg"
            else:
                item["thumbnail_url"] = None
        else:
            item["thumbnail_url"] = None
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context=_ctx(request, {
            "user": user,
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


# --- Public HTMX routes ---

@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html", context=_ctx(request))
