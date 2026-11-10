"""Proteções de borda: origem das requisições, cabeçalhos e limite de tentativas.

* **CSRF** — o cookie de sessão já é ``SameSite=Lax``, o que impede outro site
  de mandar um POST com a sessão de quem está logado. Como segunda camada,
  requisições que mudam dados (POST, PUT, PATCH, DELETE) vindas de um
  navegador precisam ter ``Origin`` (ou, na falta dele, ``Referer``) igual ao
  próprio site. Clientes sem esses cabeçalhos (scripts, testes) continuam
  funcionando: quem não é navegador não carrega o cookie de outra pessoa.
* **Cabeçalhos** — impedem que o WikiDev seja aberto dentro de um iframe de
  outro site (clickjacking), que o navegador "adivinhe" tipos de arquivo e que
  o link de redefinição de senha vaze no ``Referer``. O ``connect-src`` limita
  para onde o JavaScript da página (e o Python que roda no iframe isolado, que
  herda a política) pode fazer requisições: o próprio site e o CDN do Pyodide.
* **Força bruta** — um limite simples, em memória, de tentativas de login por
  usuário e de pedidos de recuperação por e-mail. Basta para o processo único
  do uvicorn com que o projeto roda.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "object-src 'none'",
        "form-action 'self'",
        "connect-src 'self' https://cdn.jsdelivr.net",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def _netloc(url: str | None) -> str | None:
    if not url or url == "null":
        return None
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return parts.netloc.lower()


def is_same_origin_request(request: Request, extra_hosts: set[str] | None = None) -> bool:
    """Diz se uma requisição que altera dados pode ter vindo de outro site."""
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    if origin is None and referer is None:
        return True  # cliente que não é navegador (curl, testes, integrações)
    source = _netloc(origin) if origin is not None else _netloc(referer)
    if source is None:
        return False  # "Origin: null" vem de iframes isolados e redirecionamentos
    allowed = {(request.headers.get("host") or "").lower()}
    allowed.update(extra_hosts or set())
    return source in allowed


def csrf_rejection() -> Response:
    return JSONResponse(
        status_code=403,
        content={"detail": "Requisição de outra origem recusada"},
    )


class AttemptLimiter:
    """Janela deslizante: no máximo ``limit`` tentativas por chave a cada ``window`` s."""

    def __init__(self, limit: int, window: float, clock=time.monotonic) -> None:
        self.limit = limit
        self.window = window
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float]:
        hits = self._hits.get(key)
        if hits is None:
            return deque()
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if not hits:
            self._hits.pop(key, None)
        return hits

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._recent(key, self._clock())) >= self.limit

    def hit(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            hits = self._recent(key, now)
            hits.append(now)
            self._hits[key] = hits

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


# 10 senhas erradas para o mesmo usuário em 15 min bloqueiam novas tentativas
# por um tempo; 5 pedidos de recuperação por e-mail por hora evitam spam.
login_failures = AttemptLimiter(limit=10, window=15 * 60)
password_reset_requests = AttemptLimiter(limit=5, window=60 * 60)
