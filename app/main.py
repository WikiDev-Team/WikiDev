from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError

from .db import init_db, engine
from .models import Folder, Language, Page, Tag, User
from .dependencies import get_current_user
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
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        pages = session.exec(
            select(Page).order_by(Page.created_at.desc())
        ).all()

    return templates.TemplateResponse(
        request=request,
        name="main.html",
        context={
            "project": "WikiDev",
            "usuario": current_user,
            "pages": pages,
        },
    )

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        request=request,
        name="user_profile.html",
        context={
            "project": "WikiDev",
            "usuario": current_user
        }
    )
