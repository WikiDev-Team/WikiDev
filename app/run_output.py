"""Saída salva de blocos de Python executados no navegador.

O navegador de quem edita a página roda o código (Pyodide, num iframe isolado)
e manda o resultado para cá. Como esse resultado vem do cliente, tudo é
validado antes de ir para o banco: textos têm tamanho máximo e só aceitamos
imagens PNG de verdade, em base64 estrito. Na hora de exibir, os textos passam
pelo escape do Jinja e as imagens viram <img src="data:image/png;base64,...">.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

MAX_TEXT_CHARS = 20_000
MAX_IMAGES = 6
MAX_IMAGE_BYTES = 600_000
MAX_TOTAL_IMAGE_BYTES = 1_500_000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


class RunOutputError(ValueError):
    pass


def _clip(text: str | None) -> str:
    text = text or ""
    if len(text) > MAX_TEXT_CHARS:
        return text[:MAX_TEXT_CHARS] + "\n… (saída cortada)"
    return text


class RunOutputPayload(BaseModel):
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    ms: int = Field(default=0, ge=0, le=10 * 60 * 1000)
    images: list[str] = Field(default_factory=list)

    @field_validator("stdout", "stderr", "error")
    @classmethod
    def clip_text(cls, value: str | None) -> str | None:
        return None if value is None else _clip(value)


def _validate_png(data: str) -> int:
    if not isinstance(data, str) or not _BASE64_RE.match(data) or len(data) % 4:
        raise RunOutputError("Imagem inválida")
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RunOutputError("Imagem inválida") from exc
    if not raw.startswith(PNG_SIGNATURE):
        raise RunOutputError("Só imagens PNG são aceitas")
    if len(raw) > MAX_IMAGE_BYTES:
        raise RunOutputError("Imagem grande demais")
    return len(raw)


def serialize_run_output(payload: RunOutputPayload) -> str:
    if len(payload.images) > MAX_IMAGES:
        raise RunOutputError(f"No máximo {MAX_IMAGES} gráficos por bloco")
    total = sum(_validate_png(image) for image in payload.images)
    if total > MAX_TOTAL_IMAGE_BYTES:
        raise RunOutputError("Os gráficos somam mais do que o permitido")
    return json.dumps(payload.model_dump(), ensure_ascii=False)


def parse_run_output(raw: str | None) -> dict[str, Any] | None:
    """Lê a saída salva; qualquer coisa estranha no banco é ignorada."""
    if not raw:
        return None
    try:
        data = RunOutputPayload.model_validate(json.loads(raw))
        for image in data.images:
            _validate_png(image)
    except (ValueError, TypeError, RunOutputError):
        return None
    return data.model_dump()
