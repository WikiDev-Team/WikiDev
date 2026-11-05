"""Navegação: árvore lateral, breadcrumbs, favoritas, visitas e filtros da home."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.crud import create_user
from app.models import (
    Friendship,
    FriendshipStatus,
    Page,
    PageFavorite,
    PageRevision,
    PageVisit,
    UserCreate,
)
from app.navigation import BROWSE_PAGE_SIZE, TREE_PAGE_SIZE
from app.security import generate_session_token, hash_token

HX = {"HX-Request": "true"}


def _user(client: TestClient, engine, username: str) -> tuple[int, str]:
    token = generate_session_token()
    with Session(engine) as session:
        user = create_user(
            session,
            UserCreate(username=username, email=f"{username}@example.com", display_name=username.title(), password="secret123"),
        )
        user.token = hash_token(token)
        session.add(user)
        session.commit()
        user_id = user.id
    client.cookies.set("session_token", token)
    return user_id, token


def _login(client: TestClient, token: str) -> None:
    client.cookies.set("session_token", token)


def _befriend(engine, first: int, second: int) -> None:
    with Session(engine) as session:
        session.add(Friendship(requester_id=first, addressee_id=second, status=FriendshipStatus.ACCEPTED))
        session.commit()


def _page(client: TestClient, title: str, *, visibility: str = "public", folder_id: int | None = None, tags: str = "") -> int:
    response = client.post(
        "/pages/",
        data={
            "title": title,
            "summary": f"Resumo de {title}",
            "status": "published",
            "visibility": visibility,
            "folder_id": str(folder_id or ""),
            "tags": tags,
        },
        headers=HX,
    )
    assert response.status_code == 200, response.text
    with_title = [page for page in client.get("/pages/").json() if page["title"] == title]
    return with_title[-1]["id"]


def _folder(client: TestClient, name: str, parent_id: int | None = None, visibility: str = "public") -> int:
    payload = {"name": name, "visibility": visibility}
    if parent_id is not None:
        payload["parent_folder_id"] = parent_id
    response = client.post("/folders/", json=payload)
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


# ── Breadcrumbs e árvore ─────────────────────────────────────────────────────


def test_breadcrumb_shows_whole_folder_path(client: TestClient, engine):
    _user(client, engine, "ada")
    root = _folder(client, "Linguagens")
    child = _folder(client, "Python", root)
    leaf = _folder(client, "Testes", child)
    page_id = _page(client, "Fixtures", folder_id=leaf)

    html = client.get(f"/p/{page_id}").text
    crumbs = html[html.index('class="breadcrumb"'):]
    crumbs = crumbs[: crumbs.index("</nav>")]
    assert crumbs.index("Linguagens") < crumbs.index("Python") < crumbs.index("Testes") < crumbs.index("Fixtures")

    folder_html = client.get(f"/folders/{leaf}/panel", headers=HX).text
    folder_crumbs = folder_html[folder_html.index('class="breadcrumb"'):]
    folder_crumbs = folder_crumbs[: folder_crumbs.index("</nav>")]
    assert "Linguagens" in folder_crumbs and "Python" in folder_crumbs
    assert f'data-folder-chain="{root},{child},{leaf}"' in folder_html


def test_tree_expands_current_folder_and_lazy_loads_others(client: TestClient, engine):
    _user(client, engine, "ada")
    open_root = _folder(client, "Aberta")
    open_child = _folder(client, "Sub", open_root)
    closed = _folder(client, "Fechada")
    inside = _page(client, "Dentro da sub", folder_id=open_child)
    _page(client, "Na fechada", folder_id=closed)

    html = client.get(f"/p/{inside}").text
    tree = html[html.index('id="sidebar-nav"'):]
    # Pastas acima da página aberta já vêm abertas e com as páginas.
    assert f'data-folder-id="{open_root}" open' in tree
    assert f'data-folder-id="{open_child}" open' in tree
    assert f'id="tree-page-{inside}"' in tree
    # A outra pasta vem fechada e carrega as páginas sob demanda.
    assert f'data-folder-id="{closed}" hx-get="/nav/pastas/{closed}"' in tree
    assert "Na fechada" not in tree

    lazy = client.get(f"/nav/pastas/{closed}", headers=HX)
    assert lazy.status_code == 200
    assert "Na fechada" in lazy.text


def test_tree_endpoint_respects_folder_permissions(client: TestClient, engine):
    _, owner = _user(client, engine, "dona")
    private = _folder(client, "Segredo", visibility="private")
    _page(client, "Página secreta", folder_id=private)
    _user(client, engine, "visitante")

    assert client.get(f"/nav/pastas/{private}", headers=HX).status_code == 404
    assert "Segredo" not in client.get("/dashboard").text


def test_tree_paginates_long_lists(client: TestClient, engine):
    _user(client, engine, "ada")
    total = TREE_PAGE_SIZE + 5
    for index in range(total):
        _page(client, f"Página {index:03d}")

    html = client.get("/dashboard").text
    assert html.count('class="tree-leaf"') == TREE_PAGE_SIZE
    assert f"/nav/sem-pasta?offset={TREE_PAGE_SIZE}" in html
    assert "Mostrar mais 5" in html

    more = client.get(f"/nav/sem-pasta?offset={TREE_PAGE_SIZE}", headers=HX).text
    assert more.count('class="tree-leaf"') == 5
    assert "Mostrar mais" not in more


def test_creating_page_refreshes_sidebar_tree(client: TestClient, engine):
    _user(client, engine, "ada")
    response = client.post("/pages/", data={"title": "Nova nota", "status": "published"}, headers=HX)
    assert 'id="sidebar-nav" class="sidebar-nav" hx-swap-oob="outerHTML"' in response.text
    assert "Nova nota" in response.text[response.text.index('id="sidebar-nav"'):]


# ── Favoritas e visitas ──────────────────────────────────────────────────────


def test_favorite_toggle_shows_on_home_and_sidebar(client: TestClient, engine, session: Session):
    user_id, _ = _user(client, engine, "ada")
    page_id = _page(client, "Guardar para depois")

    response = client.post(f"/pages/{page_id}/favorite", headers=HX)
    assert response.status_code == 200
    assert 'aria-pressed="true"' in response.text
    assert 'id="sidebar-favorites"' in response.text and "hx-swap-oob" in response.text
    assert session.get(PageFavorite, (user_id, page_id)) is not None

    home = client.get("/dashboard").text
    favorites = home[home.index('id="qs-favorites"'):home.index('id="qs-recent"')]
    assert "Guardar para depois" in favorites
    assert 'aria-pressed="true"' in client.get(f"/pages/{page_id}/blocks-editor", headers=HX).text

    response = client.post(f"/pages/{page_id}/favorite", headers=HX)
    assert 'aria-pressed="false"' in response.text
    session.expire_all()
    assert session.get(PageFavorite, (user_id, page_id)) is None


def test_cannot_favorite_invisible_page(client: TestClient, engine):
    _user(client, engine, "dona")
    private_id = _page(client, "Diário", visibility="private")
    _user(client, engine, "curioso")
    assert client.post(f"/pages/{private_id}/favorite", headers=HX).status_code == 404


def test_views_feed_recent_and_most_viewed(client: TestClient, engine, session: Session):
    user_id, _ = _user(client, engine, "ada")
    popular = _page(client, "Popular")
    other = _page(client, "Pouco vista")
    for _ in range(3):
        client.get(f"/pages/{popular}/blocks-editor", headers=HX)
    client.get(f"/p/{other}")

    visit = session.get(PageVisit, (user_id, popular))
    assert visit is not None and visit.count == 3

    home = client.get("/dashboard").text
    recent = home[home.index('id="qs-recent"'):home.index('id="qs-popular"')]
    assert recent.index("Pouco vista") < recent.index("Popular")
    popular_section = home[home.index('id="qs-popular"'):home.index('id="browser-title"')]
    assert popular_section.index("Popular") < popular_section.index("Pouco vista")
    assert "3 visualizações" in popular_section


def test_deleting_page_removes_favorites_and_visits(client: TestClient, engine, session: Session):
    _user(client, engine, "ada")
    page_id = _page(client, "Temporária")
    client.post(f"/pages/{page_id}/favorite", headers=HX)
    client.get(f"/p/{page_id}")
    assert client.delete(f"/pages/{page_id}", headers=HX).status_code == 200
    session.expire_all()
    assert session.exec(select(PageFavorite).where(PageFavorite.page_id == page_id)).first() is None
    assert session.exec(select(PageVisit).where(PageVisit.page_id == page_id)).first() is None


# ── Filtros e ordenação ──────────────────────────────────────────────────────


def _setup_people(client: TestClient, engine):
    ada_id, ada = _user(client, engine, "ada")
    _page(client, "Minha sobre Python", tags="python")
    _page(client, "Minha sobre SQL", tags="sql")
    bia_id, bia = _user(client, engine, "bia")
    _page(client, "Da amiga", tags="python")
    _page(client, "Só para amigos da Bia", visibility="friends")
    _, caio = _user(client, engine, "caio")
    _page(client, "De um desconhecido")
    _page(client, "Particular do Caio", visibility="private")
    _page(client, "Para amigos do Caio", visibility="friends")
    _befriend(engine, ada_id, bia_id)
    _login(client, ada)
    return ada


def _results(client: TestClient, query: str = "") -> str:
    response = client.get(f"/home/paginas?{query}", headers=HX)
    assert response.status_code == 200
    return response.text


def test_owner_filters_split_mine_friends_and_others(client: TestClient, engine):
    _setup_people(client, engine)

    mine = _results(client, "owner=mine")
    assert "Minha sobre Python" in mine and "Minha sobre SQL" in mine
    assert "Da amiga" not in mine

    friends = _results(client, "owner=friends")
    assert "Da amiga" in friends and "Só para amigos da Bia" in friends
    assert "Minha sobre" not in friends and "desconhecido" not in friends

    others = _results(client, "owner=others")
    assert "De um desconhecido" in others
    assert "Da amiga" not in others

    everything = _results(client)
    # Nunca aparecem páginas que a pessoa não pode ver.
    assert "Particular do Caio" not in everything
    assert "Para amigos do Caio" not in everything
    assert "5 páginas" in everything


def test_tag_text_and_sort_filters(client: TestClient, engine, session: Session):
    _setup_people(client, engine)

    tagged = _results(client, "tag=python")
    assert "Minha sobre Python" in tagged and "Da amiga" in tagged
    assert "Minha sobre SQL" not in tagged

    assert "Minha sobre SQL" in _results(client, "q=sql")
    assert "Minha sobre Python" not in _results(client, "q=sql")

    alpha = _results(client, "sort=alpha")
    assert alpha.index("Da amiga") < alpha.index("De um desconhecido") < alpha.index("Minha sobre Python")

    sql_page = session.exec(select(Page).where(Page.title == "Minha sobre SQL")).one()
    for _ in range(4):
        session.add(PageRevision(page_id=sql_page.id, author_id=sql_page.author_id, title=sql_page.title))
    session.commit()
    edited = _results(client, "sort=edited")
    assert edited.index("Minha sobre SQL") < edited.index("Minha sobre Python")

    # Valores inválidos voltam ao padrão em vez de quebrar.
    assert _results(client, "owner=xyz&sort=hack&offset=abc").count('class="browse-row"') == 5


def test_filters_apply_to_dashboard_url_and_replace_history(client: TestClient, engine):
    _setup_people(client, engine)
    response = client.get("/home/paginas?owner=mine&sort=alpha", headers=HX)
    assert response.headers["HX-Replace-Url"] == "/dashboard?owner=mine&sort=alpha"

    html = client.get("/dashboard?owner=mine&sort=alpha").text
    assert '<option value="alpha" selected>' in html
    browser = html[html.index('id="browse-results"'):]
    assert "Minha sobre Python" in browser and "Da amiga" not in browser


def test_browse_list_paginates(client: TestClient, engine):
    _user(client, engine, "ada")
    total = BROWSE_PAGE_SIZE + 3
    for index in range(total):
        _page(client, f"Nota {index:03d}")

    first = _results(client, "sort=alpha")
    assert first.count('class="browse-row"') == BROWSE_PAGE_SIZE
    assert f"offset={BROWSE_PAGE_SIZE}" in first

    rest = _results(client, f"sort=alpha&offset={BROWSE_PAGE_SIZE}")
    assert rest.count('class="browse-row"') == 3
    assert "Nota 026" in rest and "Nota 000" not in rest
    assert "Mostrar mais" not in rest
