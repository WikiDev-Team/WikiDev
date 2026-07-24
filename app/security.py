from __future__ import annotations

import hashlib
import secrets

import bcrypt


def get_password_hash(password: str) -> str:
    """Gera hash bcrypt e rejeita senhas grandes demais para o algoritmo."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("A senha deve ter no máximo 72 bytes em UTF-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode("utf-8")
        if len(password_bytes) > 72:
            return False
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Permite persistir tokens sensíveis sem guardar o valor utilizável."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
