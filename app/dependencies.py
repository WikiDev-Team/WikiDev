# app/dependencies.py
from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select
from .db import get_session
from .models import User

def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:

    token = request.cookies.get("session_token")
    
    if not token:
        # redireciona para a página de login
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    ### ADIÇÃO DA COLUNA token NO BD -> ALTERAÇÃO DO BD ###
    user = session.exec(select(User).where(User.token == token)).first() 


    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida")
    
    return user