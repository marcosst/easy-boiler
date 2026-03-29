from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

MOCK_USER = {
    "name": "Usuário Demo",
    "email": "usuario@demo.com",
    "initials": "UD",
}

MOCK_PROJECTS = [
    {"id": 1, "name": "Projeto Alpha",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-blue-500 to-violet-500"},
    {"id": 2, "name": "Projeto Beta",    "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-emerald-400 to-blue-500"},
    {"id": 3, "name": "Projeto Gamma",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-amber-400 to-red-500"},
    {"id": 4, "name": "Projeto Delta",   "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-indigo-500 to-pink-500"},
    {"id": 5, "name": "Projeto Epsilon", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-cyan-400 to-teal-500"},
    {"id": 6, "name": "Projeto Zeta",    "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-rose-400 to-orange-400"},
]

_COLLECTION_COLORS = [
    "bg-gradient-to-br from-sky-400 to-blue-500",
    "bg-gradient-to-br from-violet-400 to-purple-500",
    "bg-gradient-to-br from-emerald-400 to-green-600",
    "bg-gradient-to-br from-amber-400 to-yellow-500",
    "bg-gradient-to-br from-rose-400 to-pink-500",
    "bg-gradient-to-br from-teal-400 to-cyan-500",
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


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": MOCK_USER, "projects": MOCK_PROJECTS},
    )


@app.get("/projects/{project_id}")
async def collections(request: Request, project_id: int):
    project = next((p for p in MOCK_PROJECTS if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="collections.html",
        context={
            "user": MOCK_USER,
            "project": project,
            "collections": MOCK_COLLECTIONS[project_id],
        },
    )


@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html")
