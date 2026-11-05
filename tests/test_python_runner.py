from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Page, PageBlock
from app.run_output import MAX_IMAGE_BYTES, PNG_SIGNATURE, parse_run_output

HX = {"HX-Request": "true"}
PNG = base64.b64encode(PNG_SIGNATURE + b"\x00" * 32).decode("ascii")


def _create_page(client: TestClient, title: str, **extra) -> dict:
    response = client.post("/pages/", data={"title": title, "status": "published", **extra}, headers=HX)
    assert response.status_code == 200
    return next(page for page in client.get("/pages/").json() if page["title"] == title)


def _python_block(client: TestClient, session: Session, page_id: int, code: str) -> PageBlock:
    client.post(f"/pages/{page_id}/blocks", data={"block_type": "code"}, headers=HX)
    block = session.exec(
        select(PageBlock).where(PageBlock.page_id == page_id).order_by(PageBlock.id.desc())
    ).first()
    client.patch(f"/pages/blocks/{block.id}", data={"content": code, "language": "python"}, headers=HX)
    session.refresh(block)
    return block


def test_saved_output_and_chart_are_shown_to_readers(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Gráfico", visibility="public")
    block = _python_block(client, session, page["id"], "print('oi')")

    response = client.put(
        f"/pages/blocks/{block.id}/output",
        json={"stdout": "oi <b>negrito</b>", "stderr": "", "error": None, "ms": 12, "images": [PNG]},
    )
    assert response.status_code == 204

    html = client.get(f"/p/{page['id']}").text
    assert "Saída salva com a página" in html
    assert f'src="data:image/png;base64,{PNG}"' in html
    assert "oi &lt;b&gt;negrito&lt;/b&gt;" in html
    assert "Remover saída salva" in html

    client.cookies.clear()
    register_and_login(username="bob", email="bob@example.com")
    html = client.get(f"/p/{page['id']}").text
    assert "Saída salva com a página" in html
    assert "Remover saída salva" not in html
    assert "data-output-url" not in html


def test_only_editors_can_save_output(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Só leitura", visibility="public")
    block = _python_block(client, session, page["id"], "print(1)")

    client.cookies.clear()
    register_and_login(username="eve", email="eve@example.com")
    assert client.put(f"/pages/blocks/{block.id}/output", json={"stdout": "hackeado"}).status_code == 403
    assert client.delete(f"/pages/blocks/{block.id}/output").status_code == 403
    session.refresh(block)
    assert block.run_output is None


def test_output_rejects_non_png_and_oversized_images(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Validação")
    block = _python_block(client, session, page["id"], "print(1)")
    url = f"/pages/blocks/{block.id}/output"

    svg = base64.b64encode(b"<svg onload=alert(1)>").decode("ascii")
    assert client.put(url, json={"images": [svg]}).status_code == 422
    assert client.put(url, json={"images": ['x" onerror="alert(1)']}).status_code == 422
    huge = base64.b64encode(PNG_SIGNATURE + b"\x00" * MAX_IMAGE_BYTES).decode("ascii")
    assert client.put(url, json={"images": [huge]}).status_code == 422
    assert client.put(url, json={"images": [PNG] * 7}).status_code == 422

    assert client.put(url, json={"stdout": "x" * 50_000}).status_code == 204
    session.refresh(block)
    assert len(json.loads(block.run_output)["stdout"]) < 21_000


def test_editing_code_clears_saved_output(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Muda o código")
    block = _python_block(client, session, page["id"], "print(1)")
    client.put(f"/pages/blocks/{block.id}/output", json={"stdout": "1"})

    client.patch(f"/pages/blocks/{block.id}", data={"content": "print(1)", "language": "python"}, headers=HX)
    session.refresh(block)
    assert block.run_output is not None

    client.patch(f"/pages/blocks/{block.id}", data={"content": "print(2)", "language": "python"}, headers=HX)
    session.refresh(block)
    assert block.run_output is None


def test_clear_output(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Limpar")
    block = _python_block(client, session, page["id"], "print(1)")
    client.put(f"/pages/blocks/{block.id}/output", json={"stdout": "1"})
    assert client.delete(f"/pages/blocks/{block.id}/output").status_code == 204
    session.refresh(block)
    assert block.run_output is None


def test_output_only_for_python_blocks(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Texto")
    client.post(f"/pages/{page['id']}/blocks", data={"block_type": "text"}, headers=HX)
    block = session.exec(select(PageBlock).where(PageBlock.page_id == page["id"])).first()
    assert client.put(f"/pages/blocks/{block.id}/output", json={"stdout": "x"}).status_code == 400


def test_garbage_in_database_is_ignored():
    assert parse_run_output(None) is None
    assert parse_run_output("não é json") is None
    assert parse_run_output(json.dumps({"images": ["<script>"]})) is None


def test_fork_creates_private_copy_for_reader(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Receita [pública]", visibility="public")
    block = _python_block(client, session, page["id"], "print('original')")
    client.put(f"/pages/blocks/{block.id}/output", json={"stdout": "original"})

    client.cookies.clear()
    register_and_login(username="bob", email="bob@example.com")
    response = client.post(f"/pages/blocks/{block.id}/fork", headers=HX)
    assert response.status_code == 200
    new_id = int(response.headers["HX-Redirect"].rsplit("/", 1)[1])

    fork = session.get(Page, new_id)
    assert fork.title == "Cópia de Receita [pública]"
    assert fork.visibility.value == "private"
    blocks = session.exec(select(PageBlock).where(PageBlock.page_id == new_id).order_by(PageBlock.position)).all()
    assert f"(/p/{page['id']})" in blocks[0].content
    assert "\\[pública\\]" in blocks[0].content
    assert blocks[1].content == "print('original')"
    assert blocks[1].run_output is not None

    html = client.get(f"/p/{new_id}").text
    assert "data-output-url" in html  # bob agora edita a própria cópia


def test_fork_requires_view_permission(client: TestClient, session: Session, register_and_login):
    register_and_login()
    page = _create_page(client, "Privada")
    block = _python_block(client, session, page["id"], "segredo = 1")

    client.cookies.clear()
    register_and_login(username="eve", email="eve@example.com")
    assert client.post(f"/pages/blocks/{block.id}/fork", headers=HX).status_code in (403, 404)
