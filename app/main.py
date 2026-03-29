import os

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

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/midias", StaticFiles(directory="midias"), name="midias")
templates = Jinja2Templates(directory="app/templates")

# --- Mock data (unchanged from original) ---

MOCK_PROJECTS = [
    {"id": 1, "name": "Projeto Alpha",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-teal-400 to-teal-700"},
    {"id": 2, "name": "Projeto Beta",    "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-teal-300 to-cyan-600"},
    {"id": 3, "name": "Projeto Gamma",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-emerald-400 to-teal-600"},
    {"id": 4, "name": "Projeto Delta",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-cyan-400 to-teal-500"},
    {"id": 5, "name": "Projeto Epsilon", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-teal-500 to-emerald-700"},
    {"id": 6, "name": "Projeto Zeta",    "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-cyan-300 to-teal-600"},
]

_COLLECTION_COLORS = [
    "bg-gradient-to-br from-teal-300 to-teal-600",
    "bg-gradient-to-br from-cyan-400 to-teal-700",
    "bg-gradient-to-br from-emerald-300 to-teal-500",
    "bg-gradient-to-br from-teal-400 to-cyan-600",
    "bg-gradient-to-br from-teal-500 to-emerald-600",
    "bg-gradient-to-br from-cyan-300 to-teal-500",
]

MOCK_COLLECTIONS = {
    project["id"]: [
        {
            "id": project["id"] * 10 + i,
            "name": f"Coleção {i + 1}",
            "thumbnail_url": None,
            "placeholder_color": _COLLECTION_COLORS[i],
        }
        for i in range(6)
    ]
    for project in MOCK_PROJECTS
}


def _build_mock_topics():
    """Generate mock topics for every collection."""
    topics = {}
    detail_id_counter = 1000
    details = {}

    topic_names = ["Introdução", "Conceitos Fundamentais", "Aplicações Práticas"]
    subtopic_templates = [
        ["Visão Geral", "Contexto Histórico"],
        ["Definições", "Princípios", "Modelos"],
        ["Estudo de Caso", "Exercícios"],
    ]
    detail_templates = [
        ["Resumo do tema", "Material complementar", "Vídeo explicativo"],
        ["Glossário de termos", "Diagrama conceitual"],
        ["Exemplo resolvido", "Exercício proposto", "Vídeo da aula"],
    ]

    sample_markdown = (
        "## Resumo\n\n"
        "Este é um conteúdo de exemplo em **markdown**.\n\n"
        "- Ponto importante 1\n"
        "- Ponto importante 2\n"
        "- Ponto importante 3\n\n"
        "### Observações\n\n"
        "Texto adicional com `código inline` e mais detalhes sobre o tópico."
    )

    for project in MOCK_PROJECTS:
        for col in MOCK_COLLECTIONS[project["id"]]:
            col_topics = []
            for t_idx, t_name in enumerate(topic_names):
                subtopics = []
                for s_idx, s_name in enumerate(subtopic_templates[t_idx]):
                    detail_list = []
                    for d_idx, d_name in enumerate(detail_templates[t_idx]):
                        detail_id_counter += 1
                        has_content = (d_idx % 2 == 0)
                        detail_list.append({
                            "id": detail_id_counter,
                            "name": d_name,
                            "has_content": has_content,
                        })
                        if has_content:
                            variant = detail_id_counter % 3
                            if variant == 0:
                                details[detail_id_counter] = {
                                    "name": d_name,
                                    "youtube_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                                    "content_md": sample_markdown,
                                }
                            elif variant == 1:
                                details[detail_id_counter] = {
                                    "name": d_name,
                                    "youtube_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                                    "content_md": None,
                                }
                            else:
                                details[detail_id_counter] = {
                                    "name": d_name,
                                    "youtube_url": None,
                                    "content_md": sample_markdown,
                                }
                    subtopics.append({
                        "id": col["id"] * 100 + t_idx * 10 + s_idx,
                        "name": s_name,
                        "details": detail_list,
                    })
                col_topics.append({
                    "id": col["id"] * 10 + t_idx,
                    "name": t_name,
                    "subtopics": subtopics,
                })
            topics[col["id"]] = col_topics
    return topics, details


MOCK_TOPICS, MOCK_DETAILS = _build_mock_topics()


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
    return templates.TemplateResponse(request=request, name="login.html", context={})


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
            context={"error": "Email ou senha incorretos."},
            status_code=422,
        )
    token = await create_session(db, user["id"])
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, token)
    return response


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={})


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
            context={"error": err, "username": username, "email": email},
            status_code=422,
        )
    if password != password_confirm:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": "As senhas não coincidem.", "username": username, "email": email},
            status_code=422,
        )
    row = await db.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
    if await row.fetchone():
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": "Email ou username já em uso.", "username": username, "email": email},
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
    return templates.TemplateResponse(request=request, name="choose_username.html", context={})


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
            context={"error": err, "username": username},
            status_code=422,
        )

    row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if await row.fetchone():
        return templates.TemplateResponse(
            request=request, name="choose_username.html",
            context={"error": "Username já em uso.", "username": username},
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
            context={"error": "Não foi possível obter o email do provedor."},
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


def _collect_content_details(topics_list):
    """Collect all details with content from a topics list, enriched for the drawer."""
    items = []
    for topic in topics_list:
        for subtopic in topic["subtopics"]:
            for detail in subtopic["details"]:
                if not detail["has_content"]:
                    continue
                full = MOCK_DETAILS.get(detail["id"])
                if not full:
                    continue
                thumbnail_url = None
                detail_type = "document"
                yt = full.get("youtube_url")
                if yt:
                    detail_type = "video"
                    vid = yt.rsplit("/", 1)[-1]
                    thumbnail_url = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"
                items.append({
                    "id": detail["id"],
                    "name": full["name"],
                    "type": detail_type,
                    "thumbnail_url": thumbnail_url,
                })
    return items


@app.get("/projects/{project_id}")
async def project_topics(request: Request, project_id: int, user=Depends(require_auth)):
    project = next((p for p in MOCK_PROJECTS if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404)
    first_collection = MOCK_COLLECTIONS[project_id][0]
    topics_list = MOCK_TOPICS.get(first_collection["id"], [])
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context={
            "user": user,
            "project": project,
            "topics": topics_list,
            "drawer_items": _collect_content_details(topics_list),
        },
    )


@app.get("/projects/{project_id}/collections/{collection_id}")
async def topics(request: Request, project_id: int, collection_id: int, user=Depends(require_auth)):
    project = next((p for p in MOCK_PROJECTS if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404)
    collection = next(
        (c for c in MOCK_COLLECTIONS[project_id] if c["id"] == collection_id),
        None,
    )
    if not collection:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="topics.html",
        context={
            "user": user,
            "project": project,
            "collection": collection,
            "topics": MOCK_TOPICS.get(collection_id, []),
        },
    )


@app.get("/{username}")
async def user_projects(request: Request, username: str, user=Depends(require_auth), db=Depends(get_db)):
    row = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    profile_user = await row.fetchone()
    if not profile_user:
        raise HTTPException(status_code=404)
    cursor = await db.execute(
        "SELECT id, name, shortname, image_path, created_at FROM projects WHERE owner_id = ? ORDER BY created_at DESC",
        (profile_user["id"],),
    )
    projects = await cursor.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": user, "projects": projects},
    )


# --- Public HTMX routes ---

@app.get("/htmx/details/{detail_id}")
async def htmx_detail(request: Request, detail_id: int):
    detail = MOCK_DETAILS.get(detail_id)
    if not detail:
        raise HTTPException(status_code=404)
    content_html = None
    if detail.get("content_md"):
        content_html = md.markdown(detail["content_md"])
    return templates.TemplateResponse(
        request=request,
        name="partials/detail_modal.html",
        context={
            "detail": {
                "name": detail["name"],
                "youtube_url": detail.get("youtube_url"),
                "content_html": content_html,
            }
        },
    )


@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html")
