#!/usr/bin/env python3
"""Smoke test against a running WikiDev instance using only the standard library."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def request(method: str, path: str, *, form=None, json_body=None, expected=(200,)):
    headers = {"Accept": "application/json", "HX-Request": "true"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=10) as response:
            status = response.status
            body = response.read().decode()
            response_headers = response.headers
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read().decode()
        response_headers = error.headers
    except urllib.error.URLError as error:
        raise SystemExit(f"Servidor indisponível em {BASE_URL}: {error}") from error
    if status not in expected:
        raise AssertionError(f"{method} {path}: esperado {expected}, recebido {status}: {body}")
    try:
        parsed = json.loads(body) if body else None
    except json.JSONDecodeError:
        parsed = body
    return parsed, response_headers


def main() -> None:
    suffix = str(time.time_ns())
    health, _ = request("GET", "/health")
    assert health["status"] == "healthy"

    username = f"smoke_{suffix}"
    password = "senha-smoke"
    _, headers = request(
        "POST",
        "/register",
        form={
            "username": username,
            "email": f"{username}@example.com",
            "display_name": "Smoke Test",
            "password": password,
            "password_confirm": password,
        },
    )
    assert headers.get("HX-Redirect") == "/login?registered=1"

    _, headers = request("POST", "/login", form={"username": username, "password": password})
    assert headers.get("HX-Redirect") == "/dashboard"

    dashboard, _ = request("GET", "/dashboard")
    assert "Smoke Test" in dashboard

    folder, _ = request(
        "POST",
        "/folders/",
        json_body={"name": "Pasta do smoke test", "visibility": "private"},
        expected=(201,),
    )
    page, _ = request(
        "POST",
        f"/folders/{folder['id']}/pages",
        json_body={"title": "Página do smoke test", "status": "draft", "tag_ids": []},
        expected=(201,),
    )
    assert page["folder_id"] == folder["id"]

    print("[OK] health, registro, login, dashboard, pasta e página")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"[FALHA] {error}", file=sys.stderr)
        raise SystemExit(1)
