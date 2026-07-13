from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..crud import create_code_example, update_code_example
from ..db import get_session
from ..dependencies import get_current_user
from ..models import CodeExample, CodeExampleCreate, CodeExampleRead, CodeExampleUpdate, Page, User
from ..permissions import list_accessible_pages, require_page_edit, require_page_view

router = APIRouter(prefix="/examples", tags=["examples"])


def _page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _example_or_404(session: Session, example_id: int) -> CodeExample:
    example = session.get(CodeExample, example_id)
    if example is None:
        raise HTTPException(status_code=404, detail="Exemplo não encontrado")
    return example


@router.get("/", response_model=list[CodeExampleRead])
def list_examples(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    page_id: int | None = None,
):
    stmt = select(CodeExample).order_by(CodeExample.created_at.desc())
    if page_id is not None:
        page = _page_or_404(session, page_id)
        require_page_view(session, page, current_user)
        stmt = stmt.where(CodeExample.page_id == page_id)
    else:
        accessible_ids = [page.id for page in list_accessible_pages(session, current_user.id)]
        if not accessible_ids:
            return []
        stmt = stmt.where(CodeExample.page_id.in_(accessible_ids))
    return session.exec(stmt).all()


@router.post("/", response_model=CodeExampleRead, status_code=201)
def add_example(
    payload: CodeExampleCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, payload.page_id)
    require_page_edit(session, page, current_user)
    safe_payload = payload.model_copy(update={"author_id": current_user.id})
    return create_code_example(session, safe_payload)


@router.get("/{example_id}", response_model=CodeExampleRead)
def get_example(
    example_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    example = _example_or_404(session, example_id)
    require_page_view(session, _page_or_404(session, example.page_id), current_user)
    return example


@router.patch("/{example_id}", response_model=CodeExampleRead)
def edit_example(
    example_id: int,
    payload: CodeExampleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    example = _example_or_404(session, example_id)
    require_page_edit(session, _page_or_404(session, example.page_id), current_user)
    return update_code_example(session, example, payload)


@router.delete("/{example_id}", status_code=204)
def remove_example(
    example_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    example = _example_or_404(session, example_id)
    require_page_edit(session, _page_or_404(session, example.page_id), current_user)
    session.delete(example)
    session.commit()
