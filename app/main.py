import os
import re

import markdown as md
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
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
from app.i18n import translate, SUPPORTED_LANGS
from app.i18n.middleware import LanguageMiddleware
from app.md_parser import get_detail_content, parse_topics_md

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
)
app.add_middleware(LanguageMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/midias", StaticFiles(directory="midias"), name="midias")
templates = Jinja2Templates(directory="app/templates")


def _ctx(request: Request, context: dict | None = None) -> dict:
    """Add i18n helpers to template context."""
    ctx = context or {}
    lang = getattr(request.state, "lang", "pt")
    user = ctx.get("user")
    if user and user.get("language"):
        lang = user["language"]
    ctx["_"] = lambda key: translate(key, lang)
    ctx["current_lang"] = lang
    return ctx


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
            context=_ctx(request, {"error": translate("login.invalid_credentials", request.state.lang)}),
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
            context=_ctx(request, {"error": translate(err, request.state.lang), "username": username, "email": email}),
            status_code=422,
        )
    if password != password_confirm:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context=_ctx(request, {"error": translate("register.passwords_mismatch", request.state.lang), "username": username, "email": email}),
            status_code=422,
        )
    row = await db.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
    if await row.fetchone():
        return templates.TemplateResponse(
            request=request, name="register.html",
            context=_ctx(request, {"error": translate("register.email_or_username_taken", request.state.lang), "username": username, "email": email}),
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
            context=_ctx(request, {"error": translate(err, request.state.lang), "username": username}),
            status_code=422,
        )

    row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if await row.fetchone():
        return templates.TemplateResponse(
            request=request, name="choose_username.html",
            context=_ctx(request, {"error": translate("choose_username.username_taken", request.state.lang), "username": username}),
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
            context=_ctx(request, {"error": translate("login.oauth_email_error", request.state.lang)}),
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
        "SELECT id, name, shortname, image_path, created_at FROM subjects WHERE owner_id = ? ORDER BY created_at DESC",
        (profile_user["id"],),
    )
    subjects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=_ctx(request, {"user": user, "subjects": subjects}),
    )


@app.get("/{username}/{shortname}")
async def subject_topics(request: Request, username: str, shortname: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute(
        """
        SELECT s.id, s.name, s.shortname, s.content_md, s.image_path
        FROM subjects s
        JOIN users u ON s.owner_id = u.id
        WHERE u.username = ? AND s.shortname = ?
        """,
        (username, shortname),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    topics = parse_topics_md(subject["content_md"])
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


def _youtube_embed(match):
    vid = match.group(1)
    return (
        f'<div class="aspect-video rounded-xl overflow-hidden mb-4 bg-black">'
        f'<iframe src="https://www.youtube.com/embed/{vid}" class="w-full h-full" '
        f'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
        f'gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
    )


@app.get("/htmx/details/{username}/{shortname}/{detail_id}")
async def htmx_detail(request: Request, username: str, shortname: str, detail_id: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute(
        """
        SELECT s.content_md
        FROM subjects s
        JOIN users u ON s.owner_id = u.id
        WHERE u.username = ? AND s.shortname = ?
        """,
        (username, shortname),
    )
    subject = await row.fetchone()
    if not subject:
        raise HTTPException(status_code=404)
    content = get_detail_content(subject["content_md"], detail_id)
    if content is None:
        raise HTTPException(status_code=404)
    content_html = md.markdown(content)
    content_html = YOUTUBE_RE.sub(_youtube_embed, content_html)
    return templates.TemplateResponse(
        request=request,
        name="partials/detail_modal.html",
        context=_ctx(request, {"detail": {"content_html": content_html}}),
    )


@app.post("/htmx/set-language")
async def htmx_set_language(
    request: Request,
    lang: str = Form(...),
    user=Depends(require_auth),
    db=Depends(get_db),
):
    if lang not in SUPPORTED_LANGS:
        return Response(status_code=400)
    await db.execute("UPDATE users SET language = ? WHERE id = ?", (lang, user["id"]))
    await db.commit()
    response = Response(status_code=200)
    response.headers["HX-Refresh"] = "true"
    response.set_cookie("lang", lang, max_age=365 * 86400, samesite="lax")
    return response


# --- Public HTMX routes ---

@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html", context=_ctx(request))
