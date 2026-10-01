import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.internal.dependencies import get_async_session, get_db_session


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="async_session_override", scope="session")
def async_session_override_fixture(tmp_path_factory):
    """fastapi-users (login, /me, register) reads users through its own async
    session. Point it at a throwaway SQLite file instead of the real Postgres.
    NullPool: TestClient runs each request on a fresh event loop, so a pooled
    connection from an earlier request would be bound to a closed loop.
    Session-scoped (built once): the auth tests only read from it."""
    db_file = tmp_path_factory.mktemp("auth") / "auth.db"
    SQLModel.metadata.create_all(create_engine(f"sqlite:///{db_file}"))
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", poolclass=NullPool)

    async def _get_async_session():
        async with AsyncSession(async_engine, expire_on_commit=False) as s:
            yield s

    return _get_async_session


@pytest.fixture(name="client")
def client_fixture(session: Session, async_session_override):
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_async_session] = async_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
