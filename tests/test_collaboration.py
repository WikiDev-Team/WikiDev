"""Edição simultânea: presença, sincronização de blocos e mescla ao salvar."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.collab import PresenceRegistry, merge3, presence
from app.main import app
from app.models import PageBlock, PageRevision

HX = {"HX-Request": "true"}


@pytest.fixture(autouse=True)
def _clear_presence():
    presence.clear()
    yield
    presence.clear()


# ── merge3 ───────────────────────────────────────────────────────────────────


def test_merge3_combines_changes_on_different_lines():
    base = "um\ndois\ntrês\nquatro\n"
    mine = "UM\ndois\ntrês\nquatro\n"
    theirs = "um\ndois\ntrês\nQUATRO\n"
    result = merge3(base, mine, theirs)
    assert result.clean
    assert result.content == "UM\ndois\ntrês\nQUATRO\n"


def test_merge3_keeps_both_insertions_in_different_places():
    base = "a\nb\nc"
    result = merge3(base, "início\na\nb\nc", "a\nb\nc\nfim")
    assert result.clean
    assert result.content == "início\na\nb\nc\nfim"


def test_merge3_marks_conflict_on_same_line():
    result = merge3("x = 1\n", "x = 2\n", "x = 3\n", theirs_name="Ana")
    assert result.conflicts == 1
    assert result.content == (
        "<<<<<<< Sua versão\nx = 2\n=======\nx = 3\n>>>>>>> Versão salva por Ana\n"
    )


def test_merge3_trivial_cases():
    assert merge3("a", "a", "b").content == "b"
    assert merge3("a", "b", "a").content == "b"
    assert merge3("a", "c", "c").content == "c"
    assert merge3("", "novo", "").content == "novo"


def test_presence_expires_after_ttl():
    now = [100.0]
    registry = PresenceRegistry(ttl=10, clock=lambda: now[0])

    class U:  # noqa: D401 - usuário mínimo
        def __init__(self, uid, name):
            self.id, self.username, self.display_name = uid, name, ""

    registry.touch(1, U(1, "ada"))
    registry.touch(1, U(2, "ana"), {7})
    assert [p.username for p in registry.others(1, 1)] == ["ana"]
    assert [p.username for p in registry.editing_block(1, 7, 1)] == ["ana"]
    now[0] += 11
    assert registry.others(1, 1) == []


# ── Fluxo com duas pessoas ───────────────────────────────────────────────────


def _register(client: TestClient, username: str) -> None:
    password = "senha-segura"
    client.post(
        "/register",
        data={"username": username, "email": f"{username}@example.com", "password": password,
              "password_confirm": password, "display_name": username.title()},
        headers=HX,
    )
    client.post("/login", data={"username": username, "password": password}, headers=HX)


@pytest.fixture(name="two_editors")
def two_editors_fixture(client: TestClient, session: Session):
    """Ada cria uma página pública editável por todos; Bia entra num segundo cliente."""
    _register(client, "ada")
    client.post(
        "/pages/",
        data={"title": "Juntos", "status": "published", "visibility": "public", "edit_policy": "viewers"},
        headers=HX,
    )
    page = next(p for p in client.get("/pages/").json() if p["title"] == "Juntos")
    client.post(f"/pages/{page['id']}/blocks", data={"block_type": "text"}, headers=HX)
    block = session.exec(select(PageBlock).where(PageBlock.page_id == page["id"])).first()
    client.patch(f"/pages/blocks/{block.id}", data={"content": "linha 1\nlinha 2\nlinha 3"}, headers=HX)

    other = TestClient(app)
    other.__enter__()
    _register(other, "bia")
    yield client, other, page["id"], block.id
    other.__exit__(None, None, None)


def _edit_form(client: TestClient, block_id: int) -> dict:
    html = client.get(f"/pages/blocks/{block_id}/edit", headers=HX).text
    version = re.search(r'name="base_version" value="([^"]+)"', html).group(1)
    base = re.search(r'name="base_content"[^>]*>(.*?)</textarea>', html, re.S).group(1)
    return {"base_version": version, "base_content": base, "font_size": "normal", "html": html}


def test_concurrent_edits_on_different_lines_are_merged(two_editors, session: Session):
    ada, bia, page_id, block_id = two_editors
    assert bia.get(f"/pages/blocks/{block_id}/edit", headers=HX).status_code == 200, "Bia pode editar"

    form_ada = _edit_form(ada, block_id)
    form_bia = _edit_form(bia, block_id)

    saved = bia.patch(
        f"/pages/blocks/{block_id}",
        data={**form_bia, "content": "linha 1\nlinha 2\nlinha 3 (Bia)"},
        headers=HX,
    )
    assert saved.status_code == 200

    merged = ada.patch(
        f"/pages/blocks/{block_id}",
        data={**form_ada, "content": "linha 1 (Ada)\nlinha 2\nlinha 3"},
        headers=HX,
    )
    assert merged.status_code == 200
    assert "combinadas com as de Bia" in merged.text

    session.expire_all()
    block = session.get(PageBlock, block_id)
    assert block.content == "linha 1 (Ada)\nlinha 2\nlinha 3 (Bia)"

    notes = [r.note for r in session.exec(select(PageRevision).where(PageRevision.page_id == page_id))]
    assert "Mesclada com a edição simultânea de Bia" in notes


def test_conflicting_edit_is_not_saved_and_shows_both_versions(two_editors, session: Session):
    ada, bia, _page_id, block_id = two_editors
    form_ada = _edit_form(ada, block_id)
    form_bia = _edit_form(bia, block_id)

    bia.patch(f"/pages/blocks/{block_id}", data={**form_bia, "content": "linha 1\nBIA\nlinha 3"}, headers=HX)
    response = ada.patch(
        f"/pages/blocks/{block_id}", data={**form_ada, "content": "linha 1\nADA\nlinha 3"}, headers=HX
    )
    assert "Bia salvou este bloco enquanto você editava" in response.text
    assert "&lt;&lt;&lt;&lt;&lt;&lt;&lt; Sua versão" in response.text

    session.expire_all()
    assert session.get(PageBlock, block_id).content == "linha 1\nBIA\nlinha 3"

    # O formulário de conflito já traz a versão atual como base: salvar resolve.
    version = re.search(r'name="base_version" value="([^"]+)"', response.text).group(1)
    resolved = ada.patch(
        f"/pages/blocks/{block_id}",
        data={"base_version": version, "base_content": "linha 1\nBIA\nlinha 3",
              "content": "linha 1\nADA e BIA\nlinha 3", "font_size": "normal"},
        headers=HX,
    )
    assert resolved.status_code == 200
    session.expire_all()
    assert session.get(PageBlock, block_id).content == "linha 1\nADA e BIA\nlinha 3"


def test_saving_a_block_deleted_meanwhile_keeps_the_text(two_editors):
    ada, bia, _page_id, block_id = two_editors
    form_bia = _edit_form(bia, block_id)
    ada.delete(f"/pages/blocks/{block_id}", headers=HX)
    response = bia.patch(f"/pages/blocks/{block_id}", data={**form_bia, "content": "não me perca"}, headers=HX)
    assert response.status_code == 200
    assert "excluído por outra pessoa" in response.text
    assert "não me perca" in response.text


def test_presence_shows_others_and_syncs_changed_blocks(two_editors, session: Session):
    ada, bia, page_id, block_id = two_editors
    session.expire_all()
    block = session.get(PageBlock, block_id)
    old_version = block.updated_at.isoformat()

    bia.get(f"/pages/blocks/{block_id}/edit", headers=HX)
    bia.post(f"/pages/{page_id}/presence", data={"editing": str(block_id), "known": f"{block_id}="}, headers=HX)

    first = ada.post(f"/pages/{page_id}/presence", data={"known": f"{block_id}={old_version}"}, headers=HX)
    assert "Bia também está nesta página" in first.text
    assert f"&#34;{block_id}&#34;: [&#34;Bia&#34;]" in first.text  # bloco marcado como em edição
    assert "hx-swap-oob" not in first.text  # nada mudou ainda

    form_bia = _edit_form(bia, block_id)
    bia.patch(f"/pages/blocks/{block_id}", data={**form_bia, "content": "novo texto da Bia"}, headers=HX)
    bia.post(f"/pages/{page_id}/blocks", data={"block_type": "code"}, headers=HX)
    new_block = session.exec(
        select(PageBlock).where(PageBlock.page_id == page_id).order_by(PageBlock.id.desc())
    ).first()

    synced = ada.post(f"/pages/{page_id}/presence", data={"known": f"{block_id}={old_version},999=x"}, headers=HX)
    assert f'id="block-{block_id}"' in synced.text and "novo texto da Bia" in synced.text
    assert 'hx-swap-oob="beforeend:#page-blocks-list"' in synced.text
    assert f'id="block-{new_block.id}"' in synced.text
    assert '<div id="block-999" hx-swap-oob="delete">' in synced.text

    # O bloco que a própria aba está editando nunca é trocado.
    editing = ada.post(
        f"/pages/{page_id}/presence",
        data={"known": f"{block_id}={old_version}", "editing": str(block_id)},
        headers=HX,
    )
    assert "novo texto da Bia" not in editing.text


def test_edit_form_warns_when_someone_else_is_editing(two_editors):
    ada, bia, page_id, block_id = two_editors
    bia.get(f"/pages/blocks/{block_id}/edit", headers=HX)
    html = ada.get(f"/pages/blocks/{block_id}/edit", headers=HX).text
    assert "Bia está editando este bloco agora" in html


def test_presence_requires_view_permission(client: TestClient, register_and_login):
    register_and_login()
    client.post("/pages/", data={"title": "Secreta", "status": "draft"}, headers=HX)
    page = next(p for p in client.get("/pages/").json() if p["title"] == "Secreta")
    stranger = TestClient(app)
    with stranger:
        _register(stranger, "intruso")
        response = stranger.post(f"/pages/{page['id']}/presence", data={}, headers=HX)
        assert response.status_code in (403, 404)
