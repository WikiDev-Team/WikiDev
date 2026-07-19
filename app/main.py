from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError

from .db import get_session, init_db
from .models import Friendship, FriendshipStatus, PageBlock, User
from .dependencies import get_current_user
from .permissions import can_edit_page, list_accessible_pages
from .templates import templates

from .routers.users import router as users_router
from .routers.languages import router as languages_router
from .routers.tags import router as tags_router
from .routers.folders import router as folders_router
from .routers.pages import router as pages_router
from .routers.comments import router as comments_router
from .routers.examples import router as examples_router
from .routers.auth import router as auth_router
from .routers.search import router as search_router
from .routers.page_blocks import router as page_blocks_router
from .routers.friendships import router as friendships_router
from .routers.forum import router as forum_router

app = FastAPI(title="WikiDev API", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def htmx_validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.headers.get("HX-Request"):
        errors = exc.errors()
        error_msg = errors[0].get("msg", "Erro de validação") if errors else "Dados inválidos"
        html_content = f'<div class="error-message" style="color: red;">{error_msg}</div>'
        return HTMLResponse(content=html_content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(languages_router)
app.include_router(tags_router)
app.include_router(folders_router)
app.include_router(pages_router)
app.include_router(comments_router)
app.include_router(examples_router)
app.include_router(search_router)
app.include_router(page_blocks_router)
app.include_router(friendships_router)
app.include_router(forum_router)

@app.on_event("startup")
def on_startup() -> None:
    init_db()


#@app.get("/")
#def root():
#    return {
#        "project": "WikiDev",
#        "status": "ok",
#        "description": "API para linguagens, páginas, pastas, comentários, tags e exemplos de código.",
#        "docs": "/docs",
#    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/login", response_class=HTMLResponse)
async def tela_login(request: Request):
    registered = request.query_params.get("registered") == "1"

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "project": "WikiDev",
            "registered": registered
        }
    )

@app.get("/")
async def root():
    return RedirectResponse(url="/login")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
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
    pending_friend_requests = len(
        session.exec(
            select(Friendship).where(
                (Friendship.addressee_id == current_user.id)
                & (Friendship.status == FriendshipStatus.PENDING)
            )
        ).all()
    )

    open_page_id = open_page if any(page.id == open_page for page in pages) else None
    discussion_target = None
    if open_page_id is not None and discussion == "page":
        discussion_target = f"page-discussion-panel-{open_page_id}"
    elif open_page_id is not None and discussion and discussion.startswith("block-"):
        block_id_text = discussion.removeprefix("block-")
        if block_id_text.isdigit():
            block = session.get(PageBlock, int(block_id_text))
            if block is not None and block.page_id == open_page_id:
                discussion_target = f"block-discussion-panel-{block.id}"

    return templates.TemplateResponse(
        request=request,
        name="main.html",
        context={
            "project": "WikiDev",
            "usuario": current_user,
            "pages": pages,
            "editable_page_ids": editable_page_ids,
            "pending_friend_requests": pending_friend_requests,
            "open_page_id": open_page_id,
            "discussion_target": discussion_target,
        },
    )

@app.get("/profile")
async def profile(current_user: User = Depends(get_current_user)):
    return RedirectResponse(url=f"/profile/{current_user.id}", status_code=303)
