from __future__ import annotations

from html import escape

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from .db import get_session, init_db
from .dependencies import get_current_user
from .models import Friendship, FriendshipStatus, User
from .permissions import accessible_folders, can_edit_page, list_accessible_pages
from .routers.auth import router as auth_router
from .routers.comments import router as comments_router
from .routers.examples import router as examples_router
from .routers.folders import router as folders_router
from .routers.forum import router as forum_router
from .routers.friendships import router as friendships_router
from .routers.languages import router as languages_router
from .routers.page_blocks import router as page_blocks_router
from .routers.pages import router as pages_router
from .routers.search import router as search_router
from .routers.tags import router as tags_router
from .routers.users import router as users_router
from .templates import templates

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
    friendships_router,
    forum_router,
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
    open_page: int | None = None,
    discussion: str | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pages = list_accessible_pages(session, current_user.id)
    editable_page_ids = {
        page.id for page in pages if can_edit_page(session, page, current_user)
    }
    folders = accessible_folders(session, current_user)
    owned_folders = [folder for folder in folders if folder.author_id == current_user.id]
    pending_friend_requests = len(
        session.exec(
            select(Friendship).where(
                (Friendship.addressee_id == current_user.id)
                & (Friendship.status == FriendshipStatus.PENDING)
            )
        ).all()
    )

    open_page_id = open_page if any(page.id == open_page for page in pages) else None

    open_discussion = None
    if open_page_id is not None:
        if discussion == "page":
            open_discussion = discussion
        elif (
            discussion
            and discussion.startswith("block-")
            and discussion.removeprefix("block-").isdigit()
        ):
            open_discussion = discussion

    return templates.TemplateResponse(
        request=request,
        name="main.html",
        context={
            "project": "WikiDev",
            "usuario": current_user,
            "pages": pages,
            "editable_page_ids": editable_page_ids,
            "folders": folders,
            "owned_folders": owned_folders,
            "pending_friend_requests": pending_friend_requests,
            "open_page_id": open_page_id,
            "open_discussion": open_discussion,
        },
    )


@app.get("/profile")
def profile(current_user: User = Depends(get_current_user)):
    return RedirectResponse(url=f"/profile/{current_user.id}", status_code=303)
