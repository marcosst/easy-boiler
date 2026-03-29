from fastapi import FastAPI, Request
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
    {"id": 1, "name": "Projeto Alpha", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-blue-500 to-violet-500"},
    {"id": 2, "name": "Projeto Beta", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-emerald-400 to-blue-500"},
    {"id": 3, "name": "Projeto Gamma", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-amber-400 to-red-500"},
    {"id": 4, "name": "Projeto Delta", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-indigo-500 to-pink-500"},
    {"id": 5, "name": "Projeto Epsilon", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-cyan-400 to-teal-500"},
    {"id": 6, "name": "Projeto Zeta", "thumbnail_url": None, "placeholder_color": "bg-gradient-to-br from-rose-400 to-orange-400"},
]


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"user": MOCK_USER, "projects": MOCK_PROJECTS},
    )


@app.get("/htmx/hello")
async def htmx_hello(request: Request):
    return templates.TemplateResponse(request=request, name="partials/hello.html")
