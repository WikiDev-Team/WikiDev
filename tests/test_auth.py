# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool # <-- Nova importação crucial

from app.main import app
from app.db import get_session

# 1. Configuração do Banco Temporário com StaticPool para Multi-threading
sqlite_url = "sqlite:///:memory:"
engine = create_engine(
    sqlite_url, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool # <-- Força todas as threads a usarem o mesmo banco
)

def override_get_session():
    with Session(engine) as session:
        yield session

# Mágica do FastAPI: Dizemos para a API usar o nosso banco em memória em vez do original
app.dependency_overrides[get_session] = override_get_session

@pytest.fixture(name="client")
def client_fixture():
    # Cria as tabelas, entrega o cliente de teste, e depois limpa tudo
    SQLModel.metadata.create_all(engine)
    client = TestClient(app)
    yield client
    SQLModel.metadata.drop_all(engine)

# ... (Mantenha todos os testes test_registro... e test_login... abaixo sem alterações)


# 2. Testes de Casos de Uso (Funcionais)

def test_registro_usuario_com_sucesso_htmx(client: TestClient):
    # Simulamos o envio do formulário de registro com um header HTMX
    response = client.post(
        "/register",
        data={
            "username": "turing",
            "email": "alan@computacao.com",
            "password": "senha_segura",
            "password_confirm": "senha_segura",
            "display_name": "Alan Turing"
        },
        headers={"HX-Request": "true"}
    )
    
    # Valida se a sua função redirect_htmx respondeu com os headers corretos
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/login?registered=1"

def test_registro_com_senhas_diferentes_retorna_erro_html(client: TestClient):
    # Simulamos um usuário errando a digitação da senha
    response = client.post(
        "/register",
        data={
            "username": "hopper",
            "email": "grace@computacao.com",
            "password": "senha_segura",
            "password_confirm": "senha_errada",
            "display_name": "Grace Hopper"
        }
    )
    
    # Como não redirecionou, retorna 200 OK com o fragmento HTML de erro
    assert response.status_code == 200
    assert "As senhas não coincidem." in response.text

def test_login_com_sucesso_gera_cookie_de_sessao(client: TestClient):
    # Setup: Primeiro precisamos registrar um usuário no banco temporário
    client.post(
        "/register",
        data={
            "username": "lovelace",
            "email": "ada@lovelace.com",
            "password": "senha_valida",
            "password_confirm": "senha_valida",
            "display_name": "Ada"
        }
    )
    
    # Execução: Tentamos logar com as mesmas credenciais via HTMX
    response = client.post(
        "/login",
        data={
            "username": "lovelace",
            "password": "senha_valida"
        },
        headers={"HX-Request": "true"}
    )
    
    # Asserções críticas de segurança e navegação
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/dashboard"
    # Valida se a sua rota efetivamente gerou e enviou o cookie 'session_token'
    assert "session_token" in response.cookies