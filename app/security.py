# app/security.py
import bcrypt
import secrets

def get_password_hash(password: str) -> str:
    """ gera o hash usando bcrypt """
    pwd_bytes = password.encode('utf-8')

    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)

    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ verifica se a senha em texto puro bate com o hash armazenado """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password.encode('utf-8')
        
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    
    except ValueError:
        return False

def generate_session_token() -> str:
    """ gera um token de 32 bytes em Base64 url-safe """
    return secrets.token_urlsafe(32)