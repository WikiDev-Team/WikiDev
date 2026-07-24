from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..crud import create_code_example, update_code_example
from ..db import get_session
from ..dependencies import get_current_user
from ..models import CodeExample, CodeExampleCreate, CodeExampleRead, CodeExampleUpdate, Page, User
from ..permissions import can_edit_page, can_view_page, require_page_edit, require_page_view

router = APIRouter(prefix="/examples", tags=["examples"])


def _example_or_404(session: Session, example_id: int) -> CodeExample:
    example = session.get(CodeExample, example_id)
    if example is None:
        raise HTTPException(status_code=404, detail="Exemplo não encontrado")
    return example


def _page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _can_view_example(session: Session, example: CodeExample, current_user: User) -> bool:
    page = _page_or_404(session, example.page_id)
    if not can_view_page(session, page, current_user):
        return False
    return bool(
        example.is_public
        or example.author_id == current_user.id
        or can_edit_page(session, page, current_user)
    )


@router.get("/", response_model=list[CodeExampleRead])
def list_examples(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    page_id: int | None = None,
):
    statement = select(CodeExample).order_by(CodeExample.created_at)
    if page_id is not None:
        page = _page_or_404(session, page_id)
        require_page_view(session, page, current_user)
        statement = statement.where(CodeExample.page_id == page_id)
    examples = session.exec(statement).all()
    return [item for item in examples if _can_view_example(session, item, current_user)]


@router.post("/", response_model=CodeExampleRead, status_code=status.HTTP_201_CREATED)
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
    if not _can_view_example(session, example, current_user):
        raise HTTPException(status_code=403, detail="Sem permissão para visualizar este exemplo")
    return example


@router.patch("/{example_id}", response_model=CodeExampleRead)
def edit_example(
    example_id: int,
    payload: CodeExampleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    example = _example_or_404(session, example_id)
    page = _page_or_404(session, example.page_id)
    require_page_edit(session, page, current_user)
    return update_code_example(session, example, payload)


@router.delete("/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_example(
    example_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    example = _example_or_404(session, example_id)
    page = _page_or_404(session, example.page_id)
    require_page_edit(session, page, current_user)
    session.delete(example)
    session.commit()
