# tests/test_pages.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import get_session

# 1. Configuração do Banco Temporário com StaticPool
sqlite_url = "sqlite:///:memory:"
engine = create_engine(
    sqlite_url, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

def override_get_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

@pytest.fixture(name="client")
def client_fixture():
    SQLModel.metadata.create_all(engine)
    client = TestClient(app)
    yield client
    SQLModel.metadata.drop_all(engine)

# 2. Testes da Rota de Páginas

def test_add_page_sem_autenticacao_retorna_401(client: TestClient):
    # Tentativa de criar uma página com um TestClient limpo (sem cookie)
    response = client.post(
        "/pages/",
        data={
            "title": "Página Invasora",
            "summary": "Tentando burlar a segurança",
            "page_type": "note",
            "status": "draft",
            "tag_ids": ""
        },
        headers={"HX-Request": "true"}
    )
    
    # A dependência get_current_user deve barrar no ato com 401
    assert response.status_code == 401
    assert response.json() == {"detail": "Não autenticado"}

def test_add_page_com_autenticacao_sucesso_htmx(client: TestClient):
    # 1. Setup Crítico: Registrar e logar o usuário para popular o "navegador" com o cookie
    client.post(
        "/register",
        data={
            "username": "escritor",
            "email": "escritor@wiki.com",
            "password": "senha_segura",
            "password_confirm": "senha_segura",
            "display_name": "O Escritor"
        }
    )
    client.post(
        "/login",
        data={"username": "escritor", "password": "senha_segura"},
        headers={"HX-Request": "true"}
    )
    
    # Neste momento, o 'client' está autenticado e carrega o 'session_token'
    
    # 2. Execução: Submissão do formulário HTMX
    response = client.post(
        "/pages/",
        data={
            "title": "Minha Primeira Página Protegida",
            "summary": "Resumo da página HTMX",
            "page_type": "note",
            "status": "draft",
            "tag_ids": ""
        },
        headers={"HX-Request": "true"}
    )
    
    # 3. Asserções
    assert response.status_code == 200
    
    # O seu roteador deve retornar o template partials/page_response.html
    # Vamos validar se o título que passamos no POST foi renderizado no HTML de resposta
    assert "Minha Primeira Página Protegida" in response.text