from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError

from .db import init_db, engine
from .models import Language, Page, Tag, User
from .routers.users import router as users_router
from .routers.languages import router as languages_router
from .routers.tags import router as tags_router
from .routers.pages import router as pages_router
from .routers.comments import router as comments_router
from .routers.examples import router as examples_router
from .routers.auth import router as auth_router


app = FastAPI(title="WikiDev API", version="1.0.0")

templates = Jinja2Templates(directory="templates")

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

app.include_router(users_router)
app.include_router(languages_router)
app.include_router(tags_router)
app.include_router(pages_router)
app.include_router(comments_router)
app.include_router(examples_router)
app.include_router(auth_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"project": "WikiDev"}
    )


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
