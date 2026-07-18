import os

import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import db_helper
from app.data.models.base import Base
from app.main import app

load_dotenv()
DB_HOST = os.getenv("TEST_DB_HOST", "localhost")
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://postgres:postgres@{DB_HOST}:5432/test_production_control"
)


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine):
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        table_names = ", ".join(
            f'"{table.name}"' for table in Base.metadata.sorted_tables
        )
        if table_names:
            await session.execute(
                text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE;")
            )
            await session.commit()

        yield session

        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession):
    def override_get_session():
        yield db_session

    app.dependency_overrides[db_helper.session_getter] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
