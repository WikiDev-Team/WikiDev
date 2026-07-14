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


@pytest.fixture(name="client")
def client_fixture():
    SQLModel.metadata.create_all(engine)
    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client
    SQLModel.metadata.drop_all(engine)
