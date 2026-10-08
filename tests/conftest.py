import json
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_db
from src.cli import set_admin
from src.config import settings
from src.db import Base, async_session_maker_null_pool, engine_null_pool
from src.init import redis_manager
from src.main import app, lifespan
from src.schemas.hotels import HotelAdd
from src.schemas.rooms import RoomAdd
from src.utils.db_manager import DBManager

MOCKS_DIR = Path(__file__).parent

USER_EMAIL = "user@example.com"
ADMIN_EMAIL = "admin@example.com"
PASSWORD = "correct-horse-battery"


def future(days: int) -> str:
    """Дата через ``days`` дней в ISO-формате: брони в прошлом запрещены."""
    return (date.today() + timedelta(days=days)).isoformat()


@pytest.fixture(scope="session", autouse=True)
def check_test_mode() -> None:
    assert settings.MODE == "TEST"


async def get_db_null_pool() -> AsyncGenerator[DBManager]:
    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        yield db


app.dependency_overrides[get_db] = get_db_null_pool


@pytest.fixture
async def db() -> AsyncGenerator[DBManager]:
    async for db in get_db_null_pool():
        yield db


@pytest.fixture(scope="session", autouse=True)
async def app_lifespan(check_test_mode: None) -> AsyncGenerator[None]:
    """Запускает lifespan приложения: Redis и настоящий (не замоканный) кэш."""
    async with lifespan(app):
        await redis_manager.client.flushdb()
        yield


@pytest.fixture(scope="session", autouse=True)
async def setup_db(check_test_mode: None) -> None:
    async with engine_null_pool.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    hotels_data = json.loads((MOCKS_DIR / "mock_hotels.json").read_text(encoding="utf-8"))
    rooms_data = json.loads((MOCKS_DIR / "mock_rooms.json").read_text(encoding="utf-8"))
    async with DBManager(session_factory=async_session_maker_null_pool) as db_:
        await db_.hotels.add_bulk([HotelAdd.model_validate(hotel) for hotel in hotels_data])
        await db_.rooms.add_bulk([RoomAdd.model_validate(room) for room in rooms_data])
        await db_.commit()


def make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def ac(setup_db: None, app_lifespan: None) -> AsyncGenerator[AsyncClient]:
    """Анонимный клиент."""
    async with make_client() as client:
        yield client


async def register_and_login(client: AsyncClient, email: str, *, admin: bool = False) -> None:
    await client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    if admin:
        await set_admin(email, is_admin=True)
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text


@pytest.fixture(scope="session")
async def user_ac(setup_db: None, app_lifespan: None) -> AsyncGenerator[AsyncClient]:
    """Клиент обычного пользователя (без прав администратора)."""
    async with make_client() as client:
        await register_and_login(client, USER_EMAIL)
        yield client


@pytest.fixture(scope="session")
async def admin_ac(setup_db: None, app_lifespan: None) -> AsyncGenerator[AsyncClient]:
    async with make_client() as client:
        await register_and_login(client, ADMIN_EMAIL, admin=True)
        yield client
