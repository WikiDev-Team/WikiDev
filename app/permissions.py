from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy import delete, or_
from sqlmodel import Session, select

from .models import (
    Friendship,
    FriendshipStatus,
    Page,
    PageShare,
    PageSharePermission,
    PageVisibility,
    User,
    now_utc,
)


def get_friendship_between(session: Session, first_user_id: int, second_user_id: int) -> Friendship | None:
    """Retorna a relação entre dois usuários independentemente de quem iniciou."""
    return session.exec(
        select(Friendship).where(
            or_(
                (Friendship.requester_id == first_user_id)
                & (Friendship.addressee_id == second_user_id),
                (Friendship.requester_id == second_user_id)
                & (Friendship.addressee_id == first_user_id),
            )
        )
    ).first()


def get_friend_ids(session: Session, user_id: int) -> set[int]:
    friendships = session.exec(
        select(Friendship).where(
            (Friendship.status == FriendshipStatus.ACCEPTED)
            & or_(
                Friendship.requester_id == user_id,
                Friendship.addressee_id == user_id,
            )
        )
    ).all()

    return {
        friendship.addressee_id
        if friendship.requester_id == user_id
        else friendship.requester_id
        for friendship in friendships
    }


def get_friend_users(session: Session, user_id: int) -> list[User]:
    friend_ids = get_friend_ids(session, user_id)
    if not friend_ids:
        return []

    return session.exec(
        select(User)
        .where(User.id.in_(friend_ids))
        .order_by(User.display_name, User.username)
    ).all()


def are_friends(session: Session, first_user_id: int, second_user_id: int) -> bool:
    friendship = get_friendship_between(session, first_user_id, second_user_id)
    return friendship is not None and friendship.status == FriendshipStatus.ACCEPTED


def friendship_state(friendship: Friendship | None, current_user_id: int) -> str:
    if friendship is None:
        return "none"
    if friendship.status == FriendshipStatus.ACCEPTED:
        return "friends"
    if friendship.status == FriendshipStatus.REJECTED:
        return "rejected"
    if friendship.requester_id == current_user_id:
        return "outgoing_pending"
    return "incoming_pending"


def get_page_share(session: Session, page_id: int, user_id: int) -> PageShare | None:
    return session.get(PageShare, (page_id, user_id))


def can_view_page(session: Session, page: Page, user: User) -> bool:
    if page.author_id == user.id:
        return True

    if page.visibility == PageVisibility.PUBLIC:
        return True

    if page.visibility == PageVisibility.FRIENDS and page.author_id is not None:
        return are_friends(session, page.author_id, user.id)

    if page.visibility == PageVisibility.CUSTOM:
        return get_page_share(session, page.id, user.id) is not None

    return False


def can_edit_page(session: Session, page: Page, user: User) -> bool:
    if page.author_id == user.id:
        return True

    if page.visibility != PageVisibility.CUSTOM:
        return False

    share = get_page_share(session, page.id, user.id)
    return share is not None and share.permission == PageSharePermission.EDIT


def require_page_view(session: Session, page: Page, user: User) -> None:
    if not can_view_page(session, page, user):
        # Não revela se uma página privada existe.
        raise HTTPException(status_code=404, detail="Página não encontrada")


def require_page_edit(session: Session, page: Page, user: User) -> None:
    if not can_edit_page(session, page, user):
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta página")


def require_page_owner(page: Page, user: User) -> None:
    if page.author_id != user.id:
        raise HTTPException(status_code=403, detail="Somente o autor pode realizar esta ação")


def accessible_pages_query(session: Session, user_id: int):
    friend_ids = get_friend_ids(session, user_id)
    shared_page_ids = session.exec(
        select(PageShare.page_id).where(PageShare.user_id == user_id)
    ).all()

    conditions = [
        Page.author_id == user_id,
        Page.visibility == PageVisibility.PUBLIC,
    ]

    if friend_ids:
        conditions.append(
            (Page.visibility == PageVisibility.FRIENDS)
            & Page.author_id.in_(friend_ids)
        )

    if shared_page_ids:
        conditions.append(
            (Page.visibility == PageVisibility.CUSTOM)
            & Page.id.in_(shared_page_ids)
        )

    return select(Page).where(or_(*conditions))


def list_accessible_pages(session: Session, user_id: int) -> list[Page]:
    return session.exec(
        accessible_pages_query(session, user_id).order_by(Page.created_at.desc())
    ).all()


def get_page_share_user_ids(session: Session, page_id: int) -> tuple[set[int], set[int]]:
    shares = session.exec(
        select(PageShare).where(PageShare.page_id == page_id)
    ).all()
    viewers = {share.user_id for share in shares}
    editors = {
        share.user_id
        for share in shares
        if share.permission == PageSharePermission.EDIT
    }
    return viewers, editors


def replace_page_shares(
    session: Session,
    page: Page,
    owner_id: int,
    viewer_ids: Iterable[int],
    editor_ids: Iterable[int],
) -> None:
    """Substitui os compartilhamentos específicos de uma página.

    Por segurança, apenas amizades aceitas podem receber acesso direto. Usuários
    marcados como editores também recebem automaticamente permissão de leitura.
    """
    session.exec(delete(PageShare).where(PageShare.page_id == page.id))

    if page.visibility != PageVisibility.CUSTOM:
        return

    friend_ids = get_friend_ids(session, owner_id)
    requested_viewers = {int(user_id) for user_id in viewer_ids}
    requested_editors = {int(user_id) for user_id in editor_ids}
    requested_viewers.update(requested_editors)

    allowed_viewers = requested_viewers & friend_ids
    allowed_editors = requested_editors & allowed_viewers

    for user_id in sorted(allowed_viewers):
        permission = (
            PageSharePermission.EDIT
            if user_id in allowed_editors
            else PageSharePermission.VIEW
        )
        session.add(
            PageShare(
                page_id=page.id,
                user_id=user_id,
                permission=permission,
                updated_at=now_utc(),
            )
        )
