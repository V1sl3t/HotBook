from httpx import AsyncClient

from src.init import redis_manager

API = "/api/v1/comforts"


async def test_get_comforts(ac: AsyncClient):
    resp = await ac.get(API)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_create_comfort_requires_admin(ac: AsyncClient, user_ac: AsyncClient):
    assert (await ac.post(API, json={"title": "TV"})).status_code == 401
    assert (await user_ac.post(API, json={"title": "TV"})).status_code == 403


async def test_create_comfort(admin_ac: AsyncClient):
    resp = await admin_ac.post(API, json={"title": "TV"})
    assert resp.status_code == 201
    assert resp.json()["title"] == "TV"
    assert isinstance(resp.json()["id"], int)


async def test_comforts_cache_hits_and_invalidates(ac: AsyncClient, admin_ac: AsyncClient):
    redis = redis_manager.client
    await redis.delete(*await redis.keys("fastapi-cache:comforts:*") or ["_"])

    first = (await ac.get(API)).json()
    for _ in range(4):
        assert (await ac.get(API)).json() == first
    # До исправления каждый запрос создавал новый ключ: в ключ попадал объект сессии БД.
    assert len(await redis.keys("fastapi-cache:comforts:*")) == 1

    created = (await admin_ac.post(API, json={"title": "Сейф"})).json()
    assert await redis.keys("fastapi-cache:comforts:*") == []
    assert created in (await ac.get(API)).json()
