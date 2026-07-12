# tests/test_security_bounds.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import get_session

# 1. Configuração do Banco Temporário (Idêntica à dos outros testes)
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

# 2. O Teste que agora encontrará a fixture 'client'
def test_editar_pagina_de_outro_autor_deve_falhar(client: TestClient):
    # Setup: Criar Usuário A (Dono)
    client.post("/register", data={"username": "dono", "email": "dono@wiki.com", "password": "senha123", "password_confirm": "senha123"})
    client.post("/login", data={"username": "dono", "password": "senha123"}, headers={"HX-Request": "true"})
    
    # Cria a página (ID deve ser 1)
    client.post("/pages/", data={"title": "Segredo", "summary": "Info", "page_type": "note", "status": "draft", "tag_ids": ""}, headers={"HX-Request": "true"})
    
    # Usuário B (Intruso)
    client.post("/register", data={"username": "intruso", "email": "i@wiki.com", "password": "senha123", "password_confirm": "senha123"})
    client.post("/login", data={"username": "intruso", "password": "senha123"}, headers={"HX-Request": "true"})
    
    # Execução: O intruso tenta editar a página do dono (ID 1)
    response = client.patch(
        "/pages/1", 
        data={"title": "Hacked", "summary": "Hacked", "page_type": "note", "status": "draft"},
        headers={"HX-Request": "true"}
    )
    
    # Asserção: Deve retornar 403 Forbidden
    assert response.status_code == 403