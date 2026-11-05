from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import PageBlock, PageRevision

HX = {"HX-Request": "true"}


def _create_page(client: TestClient, title: str, **extra) -> dict:
    response = client.post("/pages/", data={"title": title, "status": "published", **extra}, headers=HX)
    assert response.status_code == 200
    return next(page for page in client.get("/pages/").json() if page["title"] == title)


def _add_text_block(client: TestClient, session: Session, page_id: int, content: str) -> PageBlock:
    client.post(f"/pages/{page_id}/blocks", data={"block_type": "text"}, headers=HX)
    block = session.exec(
        select(PageBlock).where(PageBlock.page_id == page_id).order_by(PageBlock.id.desc())
    ).first()
    client.patch(f"/pages/blocks/{block.id}", data={"content": content, "font_size": "normal"}, headers=HX)
    session.refresh(block)
    return block


def _revisions(session: Session, page_id: int) -> list[PageRevision]:
    session.expire_all()
    return session.exec(
        select(PageRevision).where(PageRevision.page_id == page_id).order_by(PageRevision.id)
    ).all()


# ── Histórico ────────────────────────────────────────────────────────────────


def test_edits_create_revisions_and_coalesce(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Histórico")
    block = _add_text_block(client, session, page["id"], "primeira versão")
    client.patch(f"/pages/blocks/{block.id}", data={"content": "segunda versão"}, headers=HX)

    revisions = _revisions(session, page["id"])
    # "Página criada" + uma versão agrupada com as edições seguidas.
    assert [revision.note for revision in revisions] == ["Página criada", ""]
    assert "segunda versão" in revisions[-1].snapshot

    # Depois da janela de agrupamento, uma nova edição gera outra versão.
    revisions[-1].updated_at -= timedelta(minutes=10)
    session.add(revisions[-1])
    session.commit()
    client.patch(f"/pages/blocks/{block.id}", data={"content": "terceira versão"}, headers=HX)
    assert len(_revisions(session, page["id"])) == 3


def test_history_shows_diff(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Diff")
    _add_text_block(client, session, page["id"], "linha antiga")

    html = client.get(f"/pages/{page['id']}/history").text
    assert "Histórico de versões" in html
    assert 'class="diff-line diff-add">linha antiga' in html

    full = client.get(f"/p/{page['id']}/historico")
    assert full.status_code == 200
    assert 'id="page-history"' in full.text


def test_restore_previous_revision(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Restaurar")
    block = _add_text_block(client, session, page["id"], "conteúdo bom")
    old = _revisions(session, page["id"])[-1]
    old.updated_at -= timedelta(minutes=10)
    session.add(old)
    session.commit()
    client.patch(f"/pages/blocks/{block.id}", data={"content": "conteúdo estragado"}, headers=HX)
    _add_text_block(client, session, page["id"], "bloco extra")

    response = client.post(f"/pages/{page['id']}/history/{old.id}/restore", headers=HX)

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == f"/p/{page['id']}"
    session.expire_all()
    blocks = session.exec(select(PageBlock).where(PageBlock.page_id == page["id"])).all()
    assert [item.content for item in blocks] == ["conteúdo bom"]
    assert blocks[0].id == block.id  # o bloco original é mantido (e seus comentários)
    assert _revisions(session, page["id"])[-1].note.startswith("Restaurada")


def test_history_respects_permissions(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Privada")  # visibilidade padrão: somente o autor
    revision = _revisions(session, page["id"])[0]
    client.post("/logout")
    register_and_login(username="eve", email="eve@example.com")

    assert client.get(f"/pages/{page['id']}/history").status_code == 404
    assert client.post(f"/pages/{page['id']}/history/{revision.id}/restore").status_code in (403, 404)


# ── Tags ─────────────────────────────────────────────────────────────────────


def test_tag_page_lists_only_visible_pages(client: TestClient, register_and_login):
    register_and_login()
    _create_page(client, "Pública com tag", tags="python", visibility="public")
    _create_page(client, "Privada com tag", tags="python, segredo")
    client.post("/logout")
    register_and_login(username="bob", email="bob@example.com")

    response = client.get("/t/python")

    assert response.status_code == 200
    assert "Pública com tag" in response.text
    assert "Privada com tag" not in response.text
    assert "segredo" not in client.get("/tags/python/panel").text
    assert client.get("/t/nao-existe").status_code == 404


def test_tag_chips_link_to_tag_page(client: TestClient, register_and_login):
    register_and_login()
    page = _create_page(client, "Com chips", tags="FastAPI")
    html = client.get(f"/p/{page['id']}").text
    assert 'href="/t/fastapi"' in html


# ── Links entre páginas ──────────────────────────────────────────────────────


def test_wikilinks_resolve_and_backlinks(client: TestClient, session: Session, register_and_login):
    register_and_login()
    target = _create_page(client, "Guia de SQL")
    source = _create_page(client, "Índice")
    _add_text_block(client, session, source["id"], "Leia [[guia de sql|o guia]] e [[Inexistente]].")

    source_html = client.get(f"/p/{source['id']}").text
    assert f'<a class="wikilink" href="/p/{target["id"]}"' in source_html
    assert ">o guia</a>" in source_html
    assert 'class="wikilink wikilink-missing"' in source_html

    target_html = client.get(f"/p/{target['id']}").text
    assert "Citada em" in target_html
    assert f'href="/p/{source["id"]}"' in target_html


def test_wikilinks_do_not_leak_private_titles(client: TestClient, session: Session, register_and_login):
    register_and_login()
    _create_page(client, "Plano secreto")  # privada
    client.post("/logout")
    register_and_login(username="bob", email="bob@example.com")
    page = _create_page(client, "Página do Bob")
    _add_text_block(client, session, page["id"], "Tentando [[Plano secreto]]")

    html = client.get(f"/p/{page['id']}").text
    assert 'class="wikilink wikilink-missing"' in html
    assert 'class="wikilink" href' not in html


# ── Busca rápida ─────────────────────────────────────────────────────────────


def test_quick_search_matches_titles_and_content(client: TestClient, session: Session, register_and_login):
    register_and_login()
    _create_page(client, "Docker básico", tags="containers")
    other = _create_page(client, "Anotações soltas")
    _add_text_block(client, session, other["id"], "Use docker compose up para subir tudo.")

    html = client.get("/busca/rapida", params={"q": "docker"}).text

    assert "Docker básico" in html
    assert "Mencionado no conteúdo" in html
    assert "Anotações soltas" in html

    recent = client.get("/busca/rapida").text
    assert "Recentes" in recent


def test_quick_search_hides_private_pages(client: TestClient, session: Session, register_and_login):
    register_and_login()
    secret = _create_page(client, "Senhas do servidor")
    _add_text_block(client, session, secret["id"], "token super secreto")
    client.post("/logout")
    register_and_login(username="bob", email="bob@example.com")

    html = client.get("/busca/rapida", params={"q": "secreto"}).text
    assert "Senhas do servidor" not in html
    html = client.get("/busca/rapida", params={"q": "Senhas"}).text
    assert "Senhas do servidor" not in html


# ── Executar Python ──────────────────────────────────────────────────────────


def test_python_blocks_get_run_button(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Rodando código")
    client.post(f"/pages/{page['id']}/blocks", data={"block_type": "code"}, headers=HX)

    html = client.get(f"/p/{page['id']}").text

    assert 'class="run-code-button"' in html
    assert "/static/python-runner.js" in html
