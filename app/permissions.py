from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy import delete, or_
from sqlmodel import Session, select

from .models import (
    Folder,
    FolderShare,
    FolderVisibility,
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

def get_folder_share(
    session: Session,
    folder_id: int,
    user_id: int,
) -> FolderShare | None:
    return session.get(FolderShare, (folder_id, user_id))

def _can_view_single_folder(
    session: Session,
    folder: Folder,
    user: User,
) -> bool:
    if folder.author_id == user.id:
        return True

    if folder.visibility == FolderVisibility.PUBLIC:
        return True

    if (
        folder.visibility == FolderVisibility.FRIENDS
        and folder.author_id is not None
    ):
        return are_friends(
            session,
            folder.author_id,
            user.id,
        )

    if (
        folder.visibility == FolderVisibility.CUSTOM
        and folder.id is not None
    ):
        return get_folder_share(
            session,
            folder.id,
            user.id,
        ) is not None

    return False


def can_view_folder(
    session: Session,
    folder: Folder,
    user: User,
) -> bool:
    visited: set[int] = set()
    current: Folder | None = folder

    while current is not None:
        if current.id is None or current.id in visited:
            return False

        visited.add(current.id)

        if not _can_view_single_folder(
            session,
            current,
            user,
        ):
            return False

        if current.parent_folder_id is None:
            return True

        current = session.get(
            Folder,
            current.parent_folder_id,
        )

    return False


def can_edit_folder(folder: Folder, user: User) -> bool:
    return folder.author_id == user.id


def _folder_allows_page(session: Session, page: Page, user: User) -> bool:
    if page.folder_id is None:
        return True
    folder = session.get(Folder, page.folder_id)
    return folder is not None and can_view_folder(session, folder, user)


def can_view_page(session: Session, page: Page, user: User) -> bool:
    if page.author_id == user.id:
        return True
    if not _folder_allows_page(session, page, user):
        return False
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
    if not _folder_allows_page(session, page, user):
        return False
    if page.visibility != PageVisibility.CUSTOM:
        return False
    share = get_page_share(session, page.id, user.id)
    return share is not None and share.permission == PageSharePermission.EDIT


def require_folder_view(session: Session, folder: Folder, user: User) -> None:
    if not can_view_folder(session, folder, user):
        raise HTTPException(status_code=403, detail="Você não pode acessar esta pasta")


def require_folder_edit(folder: Folder, user: User) -> None:
    if not can_edit_folder(folder, user):
        raise HTTPException(status_code=403, detail="Você não pode alterar esta pasta")


def require_page_view(session: Session, page: Page, user: User) -> None:
    if can_view_page(session, page, user):
        return
    if page.folder_id is not None:
        folder = session.get(Folder, page.folder_id)
        if folder is not None and not can_view_folder(session, folder, user):
            raise HTTPException(status_code=403, detail="Você não pode acessar esta página")
    # Não revela a existência de páginas privadas ou compartilhamentos ausentes.
    raise HTTPException(status_code=404, detail="Página não encontrada")


def require_page_edit(session: Session, page: Page, user: User) -> None:
    if not can_edit_page(session, page, user):
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta página")


def require_page_owner(page: Page, user: User) -> None:
    if page.author_id != user.id:
        raise HTTPException(status_code=403, detail="Somente o autor pode realizar esta ação")


def accessible_pages_query(session: Session, user_id: int):
    """Consulta inicial por visibilidade; filtros de pasta são aplicados em Python."""
    friend_ids = get_friend_ids(session, user_id)
    shared_page_ids = session.exec(
        select(PageShare.page_id).where(PageShare.user_id == user_id)
    ).all()
    conditions = [Page.author_id == user_id, Page.visibility == PageVisibility.PUBLIC]
    if friend_ids:
        conditions.append(
            (Page.visibility == PageVisibility.FRIENDS) & Page.author_id.in_(friend_ids)
        )
    if shared_page_ids:
        conditions.append(
            (Page.visibility == PageVisibility.CUSTOM) & Page.id.in_(shared_page_ids)
        )
    return select(Page).where(or_(*conditions))


def list_accessible_pages(session: Session, user_id: int) -> list[Page]:
    user = session.get(User, user_id)
    if user is None:
        return []
    candidates = session.exec(
        accessible_pages_query(session, user_id).order_by(Page.created_at.desc())
    ).unique().all()
    return [page for page in candidates if can_view_page(session, page, user)]


def accessible_pages(session: Session, user: User) -> list[Page]:
    return list_accessible_pages(session, user.id)


def accessible_folders(session: Session, user: User) -> list[Folder]:
    folders = session.exec(select(Folder).order_by(Folder.name)).all()
    return [folder for folder in folders if can_view_folder(session, folder, user)]

def get_folder_share_user_ids(
    session: Session,
    folder_id: int,
) -> set[int]:
    shares = session.exec(
        select(FolderShare).where(
            FolderShare.folder_id == folder_id
        )
    ).all()

    return {
        share.user_id
        for share in shares
    }


def replace_folder_shares(
    session: Session,
    folder: Folder,
    owner_id: int,
    viewer_ids: Iterable[int] | None,
) -> None:
    if folder.id is None:
        return

    session.exec(
        delete(FolderShare).where(
            FolderShare.folder_id == folder.id
        )
    )

    if folder.visibility != FolderVisibility.CUSTOM:
        return

    friend_ids = get_friend_ids(
        session,
        owner_id,
    )

    requested_viewers: set[int] = set()

    for user_id in viewer_ids or []:
        if user_id is None:
            continue

        if isinstance(user_id, str):
            user_id = user_id.strip()

            if not user_id:
                continue

        requested_viewers.add(int(user_id))

    allowed_viewers = requested_viewers & friend_ids

    for user_id in sorted(allowed_viewers):
        session.add(
            FolderShare(
                folder_id=folder.id,
                user_id=user_id,
                updated_at=now_utc(),
            )
        )

def get_page_share_user_ids(session: Session, page_id: int) -> tuple[set[int], set[int]]:
    shares = session.exec(select(PageShare).where(PageShare.page_id == page_id)).all()
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
        session.add(
            PageShare(
                page_id=page.id,
                user_id=user_id,
                permission=(
                    PageSharePermission.EDIT
                    if user_id in allowed_editors
                    else PageSharePermission.VIEW
                ),
                updated_at=now_utc(),
            )
        )
