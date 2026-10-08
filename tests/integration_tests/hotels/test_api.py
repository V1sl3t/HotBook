import pytest
from httpx import AsyncClient

from src.init import redis_manager
from tests.conftest import future

API = "/api/v1/hotels"
SEARCH = {"date_from": future(100), "date_to": future(110)}


async def test_search_hotels_paginated(ac: AsyncClient):
    resp = await ac.get(API, params={**SEARCH, "page": 1, "per_page": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1 and body["per_page"] == 2
    assert len(body["items"]) <= 2
    assert body["total"] >= len(body["items"])


async def test_search_hotels_filters(ac: AsyncClient):
    resp = await ac.get(API, params={**SEARCH, "title": "skala"})
    assert resp.status_code == 200
    assert [hotel["title"] for hotel in resp.json()["items"]] == ["Skala"]


async def test_search_hotels_invalid_dates(ac: AsyncClient):
    resp = await ac.get(API, params={"date_from": future(10), "date_to": future(5)})
    assert resp.status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [("post", API), ("put", f"{API}/1"), ("patch", f"{API}/1"), ("delete", f"{API}/1")],
)
async def test_hotel_writes_require_admin(
    ac: AsyncClient, user_ac: AsyncClient, method: str, path: str
):
    payload = {"json": {"title": "Взлом", "location": "Нигде"}} if method != "delete" else {}
    assert (await getattr(ac, method)(path, **payload)).status_code == 401
    assert (await getattr(user_ac, method)(path, **payload)).status_code == 403


async def test_admin_hotel_crud(admin_ac: AsyncClient):
    resp = await admin_ac.post(API, json={"title": "  Новый  ", "location": "Сочи"})
    assert resp.status_code == 201
    hotel = resp.json()
    assert hotel["title"] == "Новый"

    resp = await admin_ac.patch(f"{API}/{hotel['id']}", json={"location": "Адлер"})
    assert resp.status_code == 200
    assert resp.json() == {**hotel, "location": "Адлер"}

    resp = await admin_ac.put(f"{API}/{hotel['id']}", json={"title": "Т", "location": "Л"})
    assert resp.json() == {"id": hotel["id"], "title": "Т", "location": "Л"}

    assert (await admin_ac.delete(f"{API}/{hotel['id']}")).status_code == 204
    assert (await admin_ac.get(f"{API}/{hotel['id']}")).status_code == 404


async def test_missing_hotel_gives_404(admin_ac: AsyncClient):
    assert (await admin_ac.get(f"{API}/999999")).status_code == 404
    assert (await admin_ac.patch(f"{API}/999999", json={"title": "q"})).status_code == 404
    put = await admin_ac.put(f"{API}/999999", json={"title": "q", "location": "w"})
    assert put.status_code == 404
    assert (await admin_ac.delete(f"{API}/999999")).status_code == 404


async def test_too_long_title_is_422_not_500(admin_ac: AsyncClient):
    resp = await admin_ac.post(API, json={"title": "x" * 300, "location": "Сочи"})
    assert resp.status_code == 422


async def test_delete_hotel_with_rooms_is_409(admin_ac: AsyncClient):
    hotel = (await admin_ac.post(API, json={"title": "С номерами", "location": "Сочи"})).json()
    room = {"title": "Номер", "price": 100, "quantity": 1}
    await admin_ac.post(f"{API}/{hotel['id']}/rooms", json=room)
    assert (await admin_ac.delete(f"{API}/{hotel['id']}")).status_code == 409


async def test_get_hotel_is_cached_and_invalidated(ac: AsyncClient, admin_ac: AsyncClient):
    hotel = (await admin_ac.post(API, json={"title": "Кэш", "location": "Сочи"})).json()
    redis = redis_manager.client

    for _ in range(3):
        assert (await ac.get(f"{API}/{hotel['id']}")).json()["title"] == "Кэш"
    assert len(await redis.keys(f"fastapi-cache:hotels:{API}/{hotel['id']}?*")) == 1

    await admin_ac.patch(f"{API}/{hotel['id']}", json={"title": "Кэш 2"})
    assert await redis.keys("fastapi-cache:hotels:*") == []
    assert (await ac.get(f"{API}/{hotel['id']}")).json()["title"] == "Кэш 2"
