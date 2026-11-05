from __future__ import annotations

from html import escape

from urllib.parse import quote

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from .db import get_session, init_db
from .dependencies import get_current_user
from .models import Folder, Friendship, FriendshipStatus, Page, Tag, User
from .permissions import (
    accessible_folders,
    can_edit_page,
    can_view_folder,
    can_view_page,
    get_friend_users,
    list_accessible_pages,
)
from .routers.auth import _safe_next_url
from .routers.auth import router as auth_router
from .routers.comments import router as comments_router
from .routers.examples import router as examples_router
from .routers.folders import _folder_panel_context
from .routers.folders import router as folders_router
from .routers.forum import list_recent_discussions
from .routers.forum import router as forum_router
from .routers.friendships import router as friendships_router
from .routers.history import history_context
from .routers.history import router as history_router
from .routers.languages import router as languages_router
from .routers.page_blocks import page_view_context
from .routers.page_blocks import router as page_blocks_router
from .routers.pages import router as pages_router
from .routers.search import router as search_router
from .routers.tags import router as tags_router
from .routers.tags import tag_by_slug
from .routers.users import router as users_router
from .templates import templates
from .wiki import page_tags_counts, tag_panel_context

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


@app.exception_handler(StarletteHTTPException)
async def browser_auth_redirect_handler(request: Request, exc: StarletteHTTPException):
    """Leva visitantes sem sessão ao login, preservando o link que tentaram abrir."""
    wants_html = "text/html" in request.headers.get("accept", "")
    if (
        exc.status_code == status.HTTP_401_UNAUTHORIZED
        and request.method == "GET"
        and wants_html
        and not request.headers.get("HX-Request")
    ):
        target = request.url.path
        if request.url.query:
            target = f"{target}?{request.url.query}"
        return RedirectResponse(url=f"/login?next={quote(target, safe='')}", status_code=303)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
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
    history_router,
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
            "next_url": _safe_next_url(request.query_params.get("next")),
        },
    )


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


DISCUSSION_PREFIX = "block-"


def _clean_discussion(discussion: str | None) -> str | None:
    if discussion == "page":
        return discussion
    if (
        discussion
        and discussion.startswith(DISCUSSION_PREFIX)
        and discussion.removeprefix(DISCUSSION_PREFIX).isdigit()
    ):
        return discussion
    return None


def render_workspace(
    request: Request,
    session: Session,
    current_user: User,
    *,
    open_page: Page | None = None,
    open_folder: Folder | None = None,
    open_tag: Tag | None = None,
    discussion: str | None = None,
    not_found: str | None = None,
    history_revision: int | None = None,
    show_history: bool = False,
):
    """Renderiza o workspace completo, já com a página ou pasta aberta no servidor."""
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

    context = {
        "project": "WikiDev",
        "usuario": current_user,
        "pages": pages,
        "editable_page_ids": editable_page_ids,
        "folders": folders,
        "owned_folders": owned_folders,
        "pending_friend_requests": pending_friend_requests,
        "open_page_id": open_page.id if open_page else None,
        "open_folder_id": open_folder.id if open_folder else None,
        "open_discussion": _clean_discussion(discussion) if open_page else None,
        "not_found": not_found,
        "sidebar_tags": page_tags_counts(session, pages),
        "open_tag_id": open_tag.id if open_tag else None,
    }

    if open_page is not None and show_history:
        context.update(history_context(session, open_page, current_user, history_revision))
        context["show_history"] = True
        context["document_title"] = f"Histórico · {open_page.title}"
    elif open_page is not None:
        context.update(page_view_context(session, open_page, current_user))
        context["document_title"] = open_page.title
    elif open_folder is not None:
        context.update(_folder_panel_context(session, open_folder, current_user))
        context["document_title"] = open_folder.name
    elif open_tag is not None:
        context.update(tag_panel_context(session, open_tag, current_user))
        context["document_title"] = f"#{open_tag.name}"
    else:
        recent_pages = sorted(pages, key=lambda page: page.updated_at, reverse=True)
        context.update(
            {
                "recent_pages": recent_pages[:6],
                "recent_discussions": list_recent_discussions(session, current_user)[:5],
                "stats": {
                    "my_pages": sum(1 for page in pages if page.author_id == current_user.id),
                    "folders": len(owned_folders),
                    "friends": len(get_friend_users(session, current_user.id)),
                },
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="main.html",
        context=context,
        status_code=status.HTTP_404_NOT_FOUND if not_found else status.HTTP_200_OK,
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    open_page: int | None = None,
    open_folder: int | None = None,
    discussion: str | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Links antigos com ?open_page= continuam funcionando.
    page = session.get(Page, open_page) if open_page is not None else None
    if page is not None and not can_view_page(session, page, current_user):
        page = None
    folder = None
    if page is None and open_folder is not None:
        folder = session.get(Folder, open_folder)
        if folder is not None and not can_view_folder(session, folder, current_user):
            folder = None
    return render_workspace(
        request, session, current_user, open_page=page, open_folder=folder, discussion=discussion
    )


@app.get("/p/{page_id}", response_class=HTMLResponse)
def page_permalink(
    request: Request,
    page_id: int,
    discussion: str | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = session.get(Page, page_id)
    if page is None or not can_view_page(session, page, current_user):
        return render_workspace(
            request, session, current_user,
            not_found="Esta página não existe ou você não tem acesso a ela.",
        )
    return render_workspace(request, session, current_user, open_page=page, discussion=discussion)


@app.get("/p/{page_id}/historico", response_class=HTMLResponse)
def page_history_permalink(
    request: Request,
    page_id: int,
    v: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = session.get(Page, page_id)
    if page is None or not can_view_page(session, page, current_user):
        return render_workspace(
            request, session, current_user,
            not_found="Esta página não existe ou você não tem acesso a ela.",
        )
    return render_workspace(
        request, session, current_user, open_page=page, show_history=True, history_revision=v
    )


@app.get("/t/{slug}", response_class=HTMLResponse)
def tag_permalink(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tag = tag_by_slug(session, slug)
    if tag is None:
        return render_workspace(
            request, session, current_user, not_found="Esta tag não existe."
        )
    return render_workspace(request, session, current_user, open_tag=tag)


@app.get("/pastas/{folder_id}", response_class=HTMLResponse)
def folder_permalink(
    request: Request,
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = session.get(Folder, folder_id)
    if folder is None or not can_view_folder(session, folder, current_user):
        return render_workspace(
            request, session, current_user,
            not_found="Esta pasta não existe ou você não tem acesso a ela.",
        )
    return render_workspace(request, session, current_user, open_folder=folder)


@app.get("/profile")
def profile(current_user: User = Depends(get_current_user)):
    return RedirectResponse(url=f"/profile/{current_user.id}", status_code=303)
