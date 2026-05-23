from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .db import init_db, engine
from .models import Language, Page, Tag, User
from .routers.users import router as users_router
from .routers.languages import router as languages_router
from .routers.tags import router as tags_router
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
        "description": "API para linguagens, páginas, comentários, tags e exemplos de código.",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/dashboard")
def dashboard():
    with Session(engine) as session:
        return {
            "users": session.exec(select(User)).all().__len__(),
            "languages": session.exec(select(Language)).all().__len__(),
            "tags": session.exec(select(Tag)).all().__len__(),
            "pages": session.exec(select(Page)).all().__len__(),
        }
