from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("path", "active_href", "has_sidebar_toggle"),
    [
        ("/dashboard", "/dashboard", True),
        ("/friends", "/friends", False),
        ("/forum", "/forum", False),
    ],
)
def test_authenticated_pages_share_complete_topbar(
    client: TestClient,
    register_and_login,
    path: str,
    active_href: str,
    has_sidebar_toggle: bool,
):
    register_and_login()

    response = client.get(path)

    assert response.status_code == 200
    assert response.text.count('<nav class="main-nav"') == 1
    for href in ("/dashboard", "/friends", "/forum"):
        assert f'href="{href}"' in response.text
    assert re.search(
        rf'<a href="{re.escape(active_href)}"[^>]*class="[^"]*active[^"]*"',
        response.text,
    )
    assert ('class="menu-hamburger"' in response.text) is has_sidebar_toggle
