import os
from datetime import timezone

import pytest_asyncio
from app.core.database import Base, get_session
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.types import TypeDecorator

# Override with a dedicated PostgreSQL test database to exercise that dialect.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


class SQLiteUTCDateTime(TypeDecorator):
    """Emulate PostgreSQL timestamptz in the lightweight test database."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value is not None else None


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine(TEST_DATABASE_URL)
    original_types = []
    if engine.dialect.name == "sqlite":
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, DateTime):
                    original_types.append((column, column.type))
                    column.type = column.type.with_variant(
                        SQLiteUTCDateTime(), "sqlite"
                    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as s:
            yield s
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()
        for column, original_type in original_types:
            column.type = original_type


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncClient:
    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
