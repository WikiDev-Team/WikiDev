from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import CodeExample, CodeExampleCreate, CodeExampleRead, CodeExampleUpdate
from ..crud import create_code_example, update_code_example

router = APIRouter(prefix="/examples", tags=["examples"])


@router.get("/", response_model=list[CodeExampleRead])
def list_examples(session: Session = Depends(get_session), page_id: int | None = None):
    stmt = select(CodeExample).order_by(CodeExample.created_at.desc())
    if page_id is not None:
        stmt = stmt.where(CodeExample.page_id == page_id)
    return session.exec(stmt).all()


@router.post("/", response_model=CodeExampleRead, status_code=201)
def add_example(payload: CodeExampleCreate, session: Session = Depends(get_session)):
    return create_code_example(session, payload)


@router.get("/{example_id}", response_model=CodeExampleRead)
def get_example(example_id: int, session: Session = Depends(get_session)):
    obj = session.get(CodeExample, example_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Exemplo não encontrado")
    return obj


@router.patch("/{example_id}", response_model=CodeExampleRead)
def edit_example(example_id: int, payload: CodeExampleUpdate, session: Session = Depends(get_session)):
    obj = session.get(CodeExample, example_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Exemplo não encontrado")
    return update_code_example(session, obj, payload)


@router.delete("/{example_id}", status_code=204)
def remove_example(example_id: int, session: Session = Depends(get_session)):
    obj = session.get(CodeExample, example_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Exemplo não encontrado")
    session.delete(obj)
    session.commit()
