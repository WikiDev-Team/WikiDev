from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import PageBlock, PageBlockType, Tag

HTML_HEADERS = {"accept": "text/html,application/xhtml+xml"}


def _create_page(client: TestClient, title: str = "Guia de Python", **extra) -> dict:
    response = client.post(
        "/pages/",
        data={"title": title, "status": "published", **extra},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    return next(page for page in client.get("/pages/").json() if page["title"] == title)


def _create_folder(client: TestClient, name: str = "Estudos") -> dict:
    response = client.post("/folders/", json={"name": name, "visibility": "private"})
    assert response.status_code == 201
    return response.json()


def test_page_permalink_renders_page_inline(client: TestClient, register_and_login):
    register_and_login()
    page = _create_page(client)

    response = client.get(f"/p/{page['id']}")

    assert response.status_code == 200
    assert "<title>Guia de Python · WikiDev</title>" in response.text
    assert 'id="page-blocks-editor"' in response.text
    assert 'data-copy-url="/p/' in response.text


def test_page_creation_pushes_permalink(client: TestClient, register_and_login):
    register_and_login()
    response = client.post(
        "/pages/",
        data={"title": "Nova", "status": "draft"},
        headers={"HX-Request": "true"},
    )
    page = client.get("/pages/").json()[0]
    assert response.headers["HX-Push-Url"] == f"/p/{page['id']}"


def test_page_permalink_hides_inaccessible_page(client: TestClient, register_and_login):
    register_and_login()
    page = _create_page(client, title="Segredo")
    client.post("/logout")
    register_and_login(username="eve", email="eve@example.com")

    response = client.get(f"/p/{page['id']}")

    assert response.status_code == 404
    assert "Segredo" not in response.text
    assert "não existe ou você não tem acesso" in response.text


def test_folder_permalink(client: TestClient, register_and_login):
    register_and_login()
    folder = _create_folder(client)

    response = client.get(f"/pastas/{folder['id']}")

    assert response.status_code == 200
    assert 'id="folder-panel"' in response.text
    assert "<title>Estudos · WikiDev</title>" in response.text
    assert client.get("/pastas/9999").status_code == 404


def test_browser_without_session_is_sent_to_login_with_next(client: TestClient):
    response = client.get("/p/1", headers=HTML_HEADERS, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Fp%2F1"
    login_page = client.get("/login", params={"next": "/p/1"})
    assert 'name="next" value="/p/1"' in login_page.text


def test_api_without_session_still_returns_401(client: TestClient):
    response = client.get("/pages/", follow_redirects=False)
    assert response.status_code == 401


def test_login_honors_only_internal_next(client: TestClient, register_and_login):
    register_and_login()
    client.post("/logout")

    internal = client.post(
        "/login",
        data={"username": "ada", "password": "senha-segura", "next": "/p/3"},
        headers={"HX-Request": "true"},
    )
    assert internal.headers["HX-Redirect"] == "/p/3"

    for unsafe in ("https://evil.example", "//evil.example", "/\\evil.example"):
        external = client.post(
            "/login",
            data={"username": "ada", "password": "senha-segura", "next": unsafe},
            headers={"HX-Request": "true"},
        )
        assert external.headers["HX-Redirect"] == "/dashboard"


def test_text_blocks_render_markdown_and_escape_html(
    client: TestClient, session: Session, register_and_login
):
    register_and_login()
    page = _create_page(client)
    block = PageBlock(
        page_id=page["id"],
        block_type=PageBlockType.TEXT,
        content=(
            "# Título\n\n**negrito** e `codigo`\n\n- item\n\n"
            "<script>alert(1)</script>\n\n[x](javascript:alert(1))"
        ),
    )
    session.add(block)
    session.commit()

    html = client.get(f"/pages/{page['id']}/blocks-editor").text

    assert "<h1>Título</h1>" in html
    assert "<strong>negrito</strong>" in html
    assert "<code>codigo</code>" in html
    assert "<li>item</li>" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert 'href="javascript:' not in html


def test_tags_are_created_from_names(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, tags="Python, fastapi, python ,  ")

    tags = session.exec(select(Tag)).all()
    assert sorted(tag.name for tag in tags) == ["Python", "fastapi"]
    html = client.get(f"/p/{page['id']}").text
    assert 'class="tag-chip"' in html

    client.patch(
        f"/pages/{page['id']}",
        data={"title": page["title"], "status": "published", "tags": "sql"},
        headers={"HX-Request": "true"},
    )
    page_json = client.get(f"/pages/{page['id']}").json()
    assert [tag["name"] for tag in page_json["tags"]] == ["sql"]


def test_dashboard_home_lists_recent_pages(client: TestClient, register_and_login):
    register_and_login()
    _create_page(client, title="Recente")

    html = client.get("/dashboard").text

    assert "Atualizadas recentemente" in html
    assert 'href="/p/' in html
    assert "Recente" in html


# ── Modo demonstração ────────────────────────────────────────────────────────


def test_login_shows_demo_account_only_in_demo_mode(client: TestClient, monkeypatch):
    from app.config import get_settings

    assert "demo-hint" not in client.get("/login").text

    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    try:
        html = client.get("/login").text
        assert "demo-hint" in html
        assert "admin123" in html
    finally:
        monkeypatch.delenv("DEMO_MODE")
        get_settings.cache_clear()


def test_base_url_falls_back_to_render_url(monkeypatch):
    from app.config import get_settings

    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://wikidev.onrender.com/")
    get_settings.cache_clear()
    try:
        assert get_settings().app_base_url == "https://wikidev.onrender.com"
    finally:
        monkeypatch.delenv("RENDER_EXTERNAL_URL")
        get_settings.cache_clear()
