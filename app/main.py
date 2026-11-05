from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .content import load
from .db import init_db
from .routers import auth, parcours

BASE = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(_: FastAPI):
    load()      # valide parcours.json : échec immédiat si le contenu est invalide
    init_db()
    yield


app = FastAPI(title="Futura", lifespan=lifespan)
app.include_router(parcours.router)
app.include_router(auth.router)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/parent", include_in_schema=False)
def parent_page():
    return FileResponse(BASE / "static" / "parent.html")


@app.get("/sw.js", include_in_schema=False)  # à la racine pour couvrir tout le scope
def sw():
    return FileResponse(BASE / "static" / "sw.js", media_type="text/javascript",
                        headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(BASE / "static" / "manifest.webmanifest", media_type="application/manifest+json")


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.mount("/labos", StaticFiles(directory=BASE / "labos"), name="labos")
