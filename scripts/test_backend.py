#!/usr/bin/env python3

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def request(method, path, payload=None, expected=(200,), query=None):
    url = BASE_URL + path

    if query:
        url += "?" + urllib.parse.urlencode(query)

    data = None
    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            raw_body = response.read().decode("utf-8")

    except urllib.error.HTTPError as error:
        status = error.code
        raw_body = error.read().decode("utf-8")

    except urllib.error.URLError as error:
        print("\nERRO: não consegui conectar na API.")
        print("Verifique se o servidor está rodando com:")
        print("uvicorn app.main:app --reload")
        print(f"\nDetalhe: {error}")
        sys.exit(1)

    if status not in expected:
        print("\nTESTE FALHOU")
        print(f"Método: {method}")
        print(f"URL: {url}")
        print(f"Status esperado: {expected}")
        print(f"Status recebido: {status}")
        print("Corpo da resposta:")
        print(raw_body)
        raise AssertionError(f"{method} {path} retornou {status}")

    if raw_body == "":
        return None

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def print_ok(message):
    print(f"[OK] {message}")


def main():
    suffix = str(time.time_ns())

    print("\nINICIANDO TESTES DO BACKEND WIKIDEV\n")

    # ------------------------------------------------------------
    # 1. Testes básicos da aplicação
    # ------------------------------------------------------------

    root = request("GET", "/")
    check(root["project"] == "WikiDev", "Endpoint / não retornou o projeto WikiDev")
    print_ok("GET /")

    health = request("GET", "/health")
    check(health["status"] == "healthy", "Endpoint /health não retornou healthy")
    print_ok("GET /health")

    dashboard = request("GET", "/dashboard")
    check("users" in dashboard, "Dashboard não retornou contagem de usuários")
    check("languages" in dashboard, "Dashboard não retornou contagem de linguagens")
    check("tags" in dashboard, "Dashboard não retornou contagem de tags")
    check("pages" in dashboard, "Dashboard não retornou contagem de páginas")
    print_ok("GET /dashboard")

    openapi = request("GET", "/openapi.json")
    paths = openapi["paths"]

    required_paths = [
        "/",
        "/health",
        "/dashboard",
        "/users/",
        "/users/{user_id}",
        "/languages/",
        "/languages/{language_id}",
        "/tags/",
        "/tags/{tag_id}",
        "/pages/",
        "/pages/{page_id}",
        "/comments/",
        "/comments/{comment_id}",
        "/examples/",
        "/examples/{example_id}",
    ]

    for path in required_paths:
        check(path in paths, f"Rota ausente no OpenAPI: {path}")

    print_ok("OpenAPI possui todas as rotas principais")

    # ------------------------------------------------------------
    # 2. Usuários
    # ------------------------------------------------------------

    user_payload = {
        "username": f"teste_user_{suffix}",
        "email": f"teste_{suffix}@email.com",
        "display_name": "Usuário de Teste",
        "bio": "Bio criada pelo teste automático",
        "avatar_url": "",
    }

    user = request("POST", "/users/", user_payload, expected=(201,))
    user_id = user["id"]
    check(user["username"] == user_payload["username"], "Usuário criado com username errado")
    print_ok("POST /users/")

    user_get = request("GET", f"/users/{user_id}")
    check(user_get["id"] == user_id, "GET /users/{id} retornou usuário errado")
    print_ok("GET /users/{user_id}")

    users = request("GET", "/users/")
    check(any(item["id"] == user_id for item in users), "Usuário criado não apareceu na listagem")
    print_ok("GET /users/")

    user_updated = request(
        "PATCH",
        f"/users/{user_id}",
        {
            "display_name": "Usuário Atualizado",
            "bio": "Bio atualizada pelo teste",
        },
    )
    check(user_updated["display_name"] == "Usuário Atualizado", "PATCH de usuário falhou")
    print_ok("PATCH /users/{user_id}")

    request("GET", "/users/999999999", expected=(404,))
    print_ok("GET /users inexistente retorna 404")

    # ------------------------------------------------------------
    # 3. Linguagens
    # ------------------------------------------------------------

    language_payload = {
        "name": f"Python Teste {suffix}",
        "slug": "",
        "description": "Linguagem criada pelo teste automático",
        "official_url": "https://www.python.org",
        "logo_url": "",
    }

    language = request("POST", "/languages/", language_payload, expected=(201,))
    language_id = language["id"]
    check(language["name"] == language_payload["name"], "Linguagem criada com nome errado")
    check(language["slug"] != "", "Slug da linguagem não foi gerado")
    print_ok("POST /languages/")

    language_get = request("GET", f"/languages/{language_id}")
    check(language_get["id"] == language_id, "GET /languages/{id} retornou linguagem errada")
    print_ok("GET /languages/{language_id}")

    languages = request("GET", "/languages/")
    check(any(item["id"] == language_id for item in languages), "Linguagem criada não apareceu na listagem")
    print_ok("GET /languages/")

    language_updated = request(
        "PATCH",
        f"/languages/{language_id}",
        {
            "description": "Descrição atualizada pelo teste",
        },
    )
    check(
        language_updated["description"] == "Descrição atualizada pelo teste",
        "PATCH de linguagem falhou",
    )
    print_ok("PATCH /languages/{language_id}")

    # ------------------------------------------------------------
    # 4. Tags
    # ------------------------------------------------------------

    tag_payload = {
        "name": f"sintaxe-teste-{suffix}",
        "slug": "",
    }

    tag = request("POST", "/tags/", tag_payload, expected=(201,))
    tag_id = tag["id"]
    check(tag["name"] == tag_payload["name"], "Tag criada com nome errado")
    check(tag["slug"] != "", "Slug da tag não foi gerado")
    print_ok("POST /tags/")

    tag_get = request("GET", f"/tags/{tag_id}")
    check(tag_get["id"] == tag_id, "GET /tags/{id} retornou tag errada")
    print_ok("GET /tags/{tag_id}")

    tags = request("GET", "/tags/")
    check(any(item["id"] == tag_id for item in tags), "Tag criada não apareceu na listagem")
    print_ok("GET /tags/")

    tag_updated = request(
        "PATCH",
        f"/tags/{tag_id}",
        {
            "name": f"sintaxe-atualizada-{suffix}",
        },
    )
    check(tag_updated["name"] == f"sintaxe-atualizada-{suffix}", "PATCH de tag falhou")
    print_ok("PATCH /tags/{tag_id}")

    # ------------------------------------------------------------
    # 5. Páginas
    # ------------------------------------------------------------

    page_payload = {
        "title": f"Laços em Python {suffix}",
        "slug": "",
        "page_type": "official",
        "status": "published",
        "summary": "Página criada pelo teste automático",
        "content": "Em Python, os principais laços são for e while.",
        "language_id": language_id,
        "author_id": user_id,
        "parent_page_id": None,
        "tag_ids": [tag_id],
    }

    page = request("POST", "/pages/", page_payload, expected=(201,))
    page_id = page["id"]
    check(page["title"] == page_payload["title"], "Página criada com título errado")
    check(page["language_id"] == language_id, "Página criada com language_id errado")
    check(page["author_id"] == user_id, "Página criada com author_id errado")
    print_ok("POST /pages/")

    page_get = request("GET", f"/pages/{page_id}")
    check(page_get["id"] == page_id, "GET /pages/{id} retornou página errada")
    print_ok("GET /pages/{page_id}")

    pages = request("GET", "/pages/")
    check(any(item["id"] == page_id for item in pages), "Página criada não apareceu na listagem")
    print_ok("GET /pages/")

    pages_filtered = request(
        "GET",
        "/pages/",
        query={
            "language_id": language_id,
            "status": "published",
            "page_type": "official",
        },
    )
    check(
        any(item["id"] == page_id for item in pages_filtered),
        "Página criada não apareceu na busca filtrada",
    )
    print_ok("GET /pages/ com filtros")

    page_updated = request(
        "PATCH",
        f"/pages/{page_id}",
        {
            "summary": "Resumo atualizado pelo teste",
            "content": "Conteúdo atualizado pelo teste automático.",
        },
    )
    check(page_updated["summary"] == "Resumo atualizado pelo teste", "PATCH de página falhou")
    print_ok("PATCH /pages/{page_id}")

    # ------------------------------------------------------------
    # 6. Comentários
    # ------------------------------------------------------------

    comment_payload = {
        "page_id": page_id,
        "author_id": user_id,
        "parent_comment_id": None,
        "body": "Comentário criado pelo teste automático",
        "is_deleted": False,
    }

    comment = request("POST", "/comments/", comment_payload, expected=(201,))
    comment_id = comment["id"]
    check(comment["page_id"] == page_id, "Comentário criado com page_id errado")
    check(comment["author_id"] == user_id, "Comentário criado com author_id errado")
    print_ok("POST /comments/")

    comment_get = request("GET", f"/comments/{comment_id}")
    check(comment_get["id"] == comment_id, "GET /comments/{id} retornou comentário errado")
    print_ok("GET /comments/{comment_id}")

    comments = request("GET", "/comments/", query={"page_id": page_id})
    check(any(item["id"] == comment_id for item in comments), "Comentário não apareceu na listagem")
    print_ok("GET /comments/ com filtro page_id")

    comment_updated = request(
        "PATCH",
        f"/comments/{comment_id}",
        {
            "body": "Comentário atualizado pelo teste",
        },
    )
    check(comment_updated["body"] == "Comentário atualizado pelo teste", "PATCH de comentário falhou")
    print_ok("PATCH /comments/{comment_id}")

    # ------------------------------------------------------------
    # 7. Exemplos de código
    # ------------------------------------------------------------

    example_payload = {
        "page_id": page_id,
        "author_id": user_id,
        "title": "Exemplo de for em Python",
        "code": "for i in range(5):\n    print(i)",
        "explanation": "Exemplo simples de laço for.",
        "language_hint": "python",
        "is_public": True,
    }

    example = request("POST", "/examples/", example_payload, expected=(201,))
    example_id = example["id"]
    check(example["page_id"] == page_id, "Exemplo criado com page_id errado")
    check(example["author_id"] == user_id, "Exemplo criado com author_id errado")
    print_ok("POST /examples/")

    example_get = request("GET", f"/examples/{example_id}")
    check(example_get["id"] == example_id, "GET /examples/{id} retornou exemplo errado")
    print_ok("GET /examples/{example_id}")

    examples = request("GET", "/examples/", query={"page_id": page_id})
    check(any(item["id"] == example_id for item in examples), "Exemplo não apareceu na listagem")
    print_ok("GET /examples/ com filtro page_id")

    example_updated = request(
        "PATCH",
        f"/examples/{example_id}",
        {
            "explanation": "Explicação atualizada pelo teste",
            "is_public": False,
        },
    )
    check(
        example_updated["explanation"] == "Explicação atualizada pelo teste",
        "PATCH de exemplo falhou",
    )
    check(example_updated["is_public"] is False, "PATCH de is_public falhou")
    print_ok("PATCH /examples/{example_id}")

    # ------------------------------------------------------------
    # 8. Dashboard depois das criações
    # ------------------------------------------------------------

    dashboard_after = request("GET", "/dashboard")
    check(dashboard_after["users"] >= dashboard["users"] + 1, "Dashboard não atualizou usuários")
    check(dashboard_after["languages"] >= dashboard["languages"] + 1, "Dashboard não atualizou linguagens")
    check(dashboard_after["tags"] >= dashboard["tags"] + 1, "Dashboard não atualizou tags")
    check(dashboard_after["pages"] >= dashboard["pages"] + 1, "Dashboard não atualizou páginas")
    print_ok("Dashboard atualizou contadores")

    # ------------------------------------------------------------
    # 9. Remoção dos dados de teste
    # ------------------------------------------------------------

    request("DELETE", f"/examples/{example_id}", expected=(204,))
    print_ok("DELETE /examples/{example_id}")

    request("DELETE", f"/comments/{comment_id}", expected=(204,))
    print_ok("DELETE /comments/{comment_id}")

    request("DELETE", f"/pages/{page_id}", expected=(204,))
    print_ok("DELETE /pages/{page_id}")

    request("DELETE", f"/tags/{tag_id}", expected=(204,))
    print_ok("DELETE /tags/{tag_id}")

    request("DELETE", f"/languages/{language_id}", expected=(204,))
    print_ok("DELETE /languages/{language_id}")

    request("DELETE", f"/users/{user_id}", expected=(204,))
    print_ok("DELETE /users/{user_id}")

    request("GET", f"/users/{user_id}", expected=(404,))
    print_ok("GET de usuário deletado retorna 404")

    print("\nTODOS OS TESTES PASSARAM\n")


if __name__ == "__main__":
    main()
