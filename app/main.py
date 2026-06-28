from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .db import init_db, engine
from .models import Folder, Language, Page, Tag, User
from .routers.users import router as users_router
from .routers.languages import router as languages_router
from .routers.tags import router as tags_router
from .routers.folders import router as folders_router
from .routers.pages import router as pages_router
from .routers.comments import router as comments_router
from .routers.examples import router as examples_router

app = FastAPI(title="WikiDev API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(languages_router)
app.include_router(tags_router)
app.include_router(folders_router)
app.include_router(pages_router)
app.include_router(comments_router)
app.include_router(examples_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root():
    return {
        "project": "WikiDev",
        "status": "ok",
        "description": "API para linguagens, páginas, pastas, comentários, tags e exemplos de código.",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/dashboard")
def dashboard():
    with Session(engine) as session:
        return {
            "users": len(session.exec(select(User)).all()),
            "languages": len(session.exec(select(Language)).all()),
            "tags": len(session.exec(select(Tag)).all()),
            "folders": len(session.exec(select(Folder)).all()),
            "pages": len(session.exec(select(Page)).all()),
        }
