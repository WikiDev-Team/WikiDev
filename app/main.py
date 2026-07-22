from __future__ import annotations

from html import escape

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from .db import get_session, init_db
from .dependencies import get_current_user
from .models import User
from .permissions import accessible_folders, accessible_pages
from .templates import templates
from .routers.auth import router as auth_router
from .routers.comments import router as comments_router
from .routers.examples import router as examples_router
from .routers.folders import router as folders_router
from .routers.languages import router as languages_router
from .routers.page_blocks import router as page_blocks_router
from .routers.pages import router as pages_router
from .routers.search import router as search_router
from .routers.tags import router as tags_router
from .routers.users import router as users_router

app = FastAPI(title="WikiDev API", version="1.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(RequestValidationError)
async def htmx_validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.headers.get("HX-Request"):
        errors = exc.errors()
        error_msg = errors[0].get("msg", "Erro de validação") if errors else "Dados inválidos"
        return HTMLResponse(
            content=f'<div class="error-message">{escape(str(error_msg))}</div>',
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


for router in (
    auth_router,
    users_router,
    languages_router,
    tags_router,
    folders_router,
    pages_router,
    comments_router,
    examples_router,
    search_router,
    page_blocks_router,
):
    app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "healthy", "version": app.version}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "project": "WikiDev",
            "registered": request.query_params.get("registered") == "1",
            "password_reset": request.query_params.get("reset") == "1",
        },
    )


@app.get("/")
def root():
    return RedirectResponse(url="/login")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pages = accessible_pages(session, current_user)
    folders = accessible_folders(session, current_user)
    owned_folders = [folder for folder in folders if folder.author_id == current_user.id]

    return templates.TemplateResponse(
        request=request,
        name="main.html",
        context={
            "project": "WikiDev",
            "usuario": current_user,
            "pages": pages,
            "folders": folders,
            "owned_folders": owned_folders,
        },
    )


@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        request=request,
        name="user_profile.html",
        context={"project": "WikiDev", "usuario": current_user},
    )
