from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.main as main_module
from app.db import get_session
from app.main import app


@pytest.fixture(name="engine")
def engine_fixture():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine, monkeypatch) -> Iterator[TestClient]:
    def override_get_session():
        with Session(engine) as session:
            yield session

    # The in-memory schema above is the database used by every request in a test.
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(name="register_and_login")
def register_and_login_fixture(client: TestClient) -> Callable[..., None]:
    def register_and_login(
        username: str = "ada",
        email: str = "ada@example.com",
        password: str = "senha-segura",
        display_name: str = "Ada",
    ) -> None:
        register = client.post(
            "/register",
            data={
                "username": username,
                "email": email,
                "password": password,
                "password_confirm": password,
                "display_name": display_name,
            },
            headers={"HX-Request": "true"},
        )
        assert register.status_code == 200
        assert register.headers.get("HX-Redirect") == "/login?registered=1"

        login = client.post(
            "/login",
            data={"username": username, "password": password},
            headers={"HX-Request": "true"},
        )
        assert login.status_code == 200
        assert login.headers.get("HX-Redirect") == "/dashboard"
        assert "session_token" in client.cookies

    return register_and_login
