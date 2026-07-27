from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import delete
from sqlmodel import Session, select

from ..db import get_session
from ..dependencies import get_current_user
from ..models import (
    Folder,
    FolderShare,
    Friendship,
    FriendshipStatus,
    Page,
    PageShare,
    User,
    now_utc,
)
from ..permissions import (
    friendship_state,
    get_friend_ids,
    get_friend_users,
    get_friendship_between,
    list_accessible_pages,
)
from ..templates import templates

router = APIRouter(tags=["friendships"])


def _safe_return_to(return_to: str, fallback: str = "/friends") -> str:
    if return_to.startswith("/") and not return_to.startswith("//"):
        return return_to
    return fallback


def _redirect(return_to: str, message: str | None = None) -> RedirectResponse:
    destination = _safe_return_to(return_to)
    if message:
        separator = "&" if "?" in destination else "?"
        destination = f"{destination}{separator}message={quote(message)}"
    return RedirectResponse(destination, status_code=303)


def _friendship_or_404(session: Session, friendship_id: int) -> Friendship:
    friendship = session.get(Friendship, friendship_id)
    if friendship is None:
        raise HTTPException(status_code=404, detail="Solicitação de amizade não encontrada")
    return friendship


@router.get("/friends", response_class=HTMLResponse)
def friends_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    incoming = session.exec(
        select(Friendship)
        .where(
            (Friendship.addressee_id == current_user.id)
            & (Friendship.status == FriendshipStatus.PENDING)
        )
        .order_by(Friendship.created_at.desc())
    ).all()
    outgoing = session.exec(
        select(Friendship)
        .where(
            (Friendship.requester_id == current_user.id)
            & (Friendship.status == FriendshipStatus.PENDING)
        )
        .order_by(Friendship.created_at.desc())
    ).all()

    incoming_users = {
        friendship.id: session.get(User, friendship.requester_id)
        for friendship in incoming
    }
    outgoing_users = {
        friendship.id: session.get(User, friendship.addressee_id)
        for friendship in outgoing
    }
    friends = get_friend_users(session, current_user.id)

    related_ids = get_friend_ids(session, current_user.id)
    related_ids.update(friendship.requester_id for friendship in incoming)
    related_ids.update(friendship.addressee_id for friendship in outgoing)
    related_ids.add(current_user.id)

    suggestions_stmt = select(User).order_by(User.display_name, User.username).limit(30)
    if related_ids:
        suggestions_stmt = suggestions_stmt.where(User.id.notin_(related_ids))
    suggestions = session.exec(suggestions_stmt).all()

    return templates.TemplateResponse(
        request=request,
        name="friends.html",
        context={
            "project": "WikiDev",
            "usuario": current_user,
            "friends": friends,
            "incoming": incoming,
            "outgoing": outgoing,
            "incoming_users": incoming_users,
            "outgoing_users": outgoing_users,
            "suggestions": suggestions,
            "message": request.query_params.get("message", ""),
        },
    )


@router.get("/profile/{user_id}", response_class=HTMLResponse)
def public_profile(
    request: Request,
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    profile_user = session.get(User, user_id)
    if profile_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    friendship = None
    state = "self"
    if profile_user.id != current_user.id:
        friendship = get_friendship_between(session, current_user.id, profile_user.id)
        state = friendship_state(friendship, current_user.id)

    visible_pages = [
        page
        for page in list_accessible_pages(session, current_user.id)
        if page.author_id == profile_user.id
    ]

    return templates.TemplateResponse(
        request=request,
        name="user_profile.html",
        context={
            "project": "WikiDev",
            "usuario": current_user,
            "profile_user": profile_user,
            "is_owner": profile_user.id == current_user.id,
            "friendship": friendship,
            "friendship_state": state,
            "visible_pages": visible_pages,
            "message": request.query_params.get("message", ""),
        },
    )


@router.post("/friendships/request/{user_id}")
def send_friend_request(
    user_id: int,
    return_to: str = Form("/friends"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode adicionar a si mesmo")

    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    existing = get_friendship_between(session, current_user.id, user_id)
    if existing is not None:
        if existing.status == FriendshipStatus.ACCEPTED:
            return _redirect(return_to, "Vocês já são amigos.")
        if existing.status == FriendshipStatus.PENDING:
            if existing.addressee_id == current_user.id:
                return _redirect(return_to, "Esse usuário já enviou uma solicitação para você.")
            return _redirect(return_to, "Solicitação já enviada.")

        # Uma solicitação rejeitada pode ser enviada novamente, reutilizando a relação.
        existing.requester_id = current_user.id
        existing.addressee_id = user_id
        existing.status = FriendshipStatus.PENDING
        existing.updated_at = now_utc()
        session.add(existing)
    else:
        session.add(
            Friendship(
                requester_id=current_user.id,
                addressee_id=user_id,
                status=FriendshipStatus.PENDING,
            )
        )

    session.commit()
    return _redirect(return_to, "Solicitação de amizade enviada.")


@router.post("/friendships/{friendship_id}/accept")
def accept_friend_request(
    friendship_id: int,
    return_to: str = Form("/friends"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    friendship = _friendship_or_404(session, friendship_id)
    if friendship.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Somente quem recebeu pode aceitar a solicitação")
    if friendship.status != FriendshipStatus.PENDING:
        raise HTTPException(status_code=409, detail="Essa solicitação não está pendente")

    friendship.status = FriendshipStatus.ACCEPTED
    friendship.updated_at = now_utc()
    session.add(friendship)
    session.commit()
    return _redirect(return_to, "Solicitação aceita.")


@router.post("/friendships/{friendship_id}/reject")
def reject_friend_request(
    friendship_id: int,
    return_to: str = Form("/friends"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    friendship = _friendship_or_404(session, friendship_id)
    if friendship.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Somente quem recebeu pode recusar a solicitação")
    if friendship.status != FriendshipStatus.PENDING:
        raise HTTPException(status_code=409, detail="Essa solicitação não está pendente")

    friendship.status = FriendshipStatus.REJECTED
    friendship.updated_at = now_utc()
    session.add(friendship)
    session.commit()
    return _redirect(return_to, "Solicitação recusada.")


@router.post("/friendships/{friendship_id}/cancel")
def cancel_friend_request(
    friendship_id: int,
    return_to: str = Form("/friends"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    friendship = _friendship_or_404(session, friendship_id)
    if friendship.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Somente quem enviou pode cancelar a solicitação")
    if friendship.status != FriendshipStatus.PENDING:
        raise HTTPException(status_code=409, detail="Essa solicitação não está pendente")

    session.delete(friendship)
    session.commit()
    return _redirect(return_to, "Solicitação cancelada.")


@router.post("/friendships/{friendship_id}/remove")
def remove_friendship(
    friendship_id: int,
    return_to: str = Form("/friends"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    friendship = _friendship_or_404(session, friendship_id)
    if current_user.id not in {friendship.requester_id, friendship.addressee_id}:
        raise HTTPException(status_code=403, detail="Você não participa dessa amizade")
    if friendship.status != FriendshipStatus.ACCEPTED:
        raise HTTPException(status_code=409, detail="A amizade não está ativa")

    first_user_id = friendship.requester_id
    second_user_id = friendship.addressee_id

    first_user_pages = session.exec(
        select(Page.id).where(Page.author_id == first_user_id)
    ).all()
    second_user_pages = session.exec(
        select(Page.id).where(Page.author_id == second_user_id)
    ).all()

    if first_user_pages:
        session.exec(
            delete(PageShare).where(
                (PageShare.page_id.in_(first_user_pages))
                & (PageShare.user_id == second_user_id)
            )
        )
    if second_user_pages:
        session.exec(
            delete(PageShare).where(
                (PageShare.page_id.in_(second_user_pages))
                & (PageShare.user_id == first_user_id)
            )
        )

    first_user_folders = session.exec(
        select(Folder.id).where(
            Folder.author_id == first_user_id
        )
    ).all()

    second_user_folders = session.exec(
        select(Folder.id).where(
            Folder.author_id == second_user_id
        )
    ).all()

    if first_user_folders:
        session.exec(
            delete(FolderShare).where(
                (
                    FolderShare.folder_id.in_(
                        first_user_folders
                    )
                )
                & (
                    FolderShare.user_id
                    == second_user_id
                )
            )
        )

    if second_user_folders:
        session.exec(
            delete(FolderShare).where(
                (
                    FolderShare.folder_id.in_(
                        second_user_folders
                    )
                )
                & (
                    FolderShare.user_id
                    == first_user_id
                )
            )
        )


    session.delete(friendship)
    session.commit()
    return _redirect(return_to, "Amizade removida e compartilhamentos diretos revogados.")
