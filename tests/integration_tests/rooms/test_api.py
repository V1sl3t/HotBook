import pytest
from httpx import AsyncClient

from tests.conftest import future

HOTELS = "/api/v1/hotels"
ROOM = {"title": "Стандарт", "description": "Тихий", "price": 1000, "quantity": 2}


@pytest.fixture
async def hotel_id(admin_ac: AsyncClient) -> int:
    resp = await admin_ac.post(HOTELS, json={"title": "Для номеров", "location": "Казань"})
    return resp.json()["id"]


@pytest.fixture
async def comfort_ids(admin_ac: AsyncClient) -> list[int]:
    titles = ("Wi-Fi", "Кондиционер")
    return [
        (await admin_ac.post("/api/v1/comforts", json={"title": t})).json()["id"] for t in titles
    ]


async def test_room_writes_require_admin(ac: AsyncClient, user_ac: AsyncClient):
    assert (await ac.post(f"{HOTELS}/1/rooms", json=ROOM)).status_code == 401
    assert (await user_ac.post(f"{HOTELS}/1/rooms", json=ROOM)).status_code == 403
    assert (await user_ac.delete(f"{HOTELS}/1/rooms/1")).status_code == 403


async def test_room_crud_with_comforts(admin_ac: AsyncClient, hotel_id: int, comfort_ids: list):
    resp = await admin_ac.post(
        f"{HOTELS}/{hotel_id}/rooms", json={**ROOM, "comforts_ids": comfort_ids}
    )
    assert resp.status_code == 201
    room = resp.json()
    assert room["hotel_id"] == hotel_id
    assert sorted(c["id"] for c in room["comforts"]) == sorted(comfort_ids)
    url = f"{HOTELS}/{hotel_id}/rooms/{room['id']}"

    # PATCH без comforts_ids не трогает удобства, с comforts_ids — заменяет.
    resp = await admin_ac.patch(url, json={"price": 1500})
    assert resp.json()["price"] == 1500
    assert len(resp.json()["comforts"]) == 2
    resp = await admin_ac.patch(url, json={"comforts_ids": comfort_ids[:1]})
    assert [c["id"] for c in resp.json()["comforts"]] == comfort_ids[:1]

    # PUT — полная замена, удобства по умолчанию очищаются.
    resp = await admin_ac.put(url, json={"title": "Люкс", "price": 9000, "quantity": 1})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Люкс" and resp.json()["description"] is None
    assert resp.json()["comforts"] == []

    # Удаление номера с удобствами не падает на внешнем ключе (ON DELETE CASCADE).
    await admin_ac.patch(url, json={"comforts_ids": comfort_ids})
    assert (await admin_ac.delete(url)).status_code == 204
    assert (await admin_ac.get(url)).status_code == 404


async def test_unknown_comfort_is_404_not_500(admin_ac: AsyncClient, hotel_id: int):
    resp = await admin_ac.post(f"{HOTELS}/{hotel_id}/rooms", json={**ROOM, "comforts_ids": [9999]})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Удобство не найдено"


async def test_duplicate_comfort_ids_are_deduplicated(
    admin_ac: AsyncClient, hotel_id: int, comfort_ids: list
):
    ids = [comfort_ids[0], comfort_ids[0]]
    resp = await admin_ac.post(f"{HOTELS}/{hotel_id}/rooms", json={**ROOM, "comforts_ids": ids})
    assert resp.status_code == 201
    assert len(resp.json()["comforts"]) == 1


async def test_room_cannot_be_moved_or_edited_via_other_hotel(admin_ac: AsyncClient, hotel_id: int):
    room = (await admin_ac.post(f"{HOTELS}/{hotel_id}/rooms", json=ROOM)).json()
    other_hotel = (await admin_ac.post(HOTELS, json={"title": "Чужой", "location": "Омск"})).json()
    other_url = f"{HOTELS}/{other_hotel['id']}/rooms/{room['id']}"

    assert (await admin_ac.put(other_url, json=ROOM)).status_code == 404
    assert (await admin_ac.patch(other_url, json={"price": 1})).status_code == 404
    assert (await admin_ac.delete(other_url)).status_code == 404
    assert (await admin_ac.get(other_url)).status_code == 404

    own = await admin_ac.get(f"{HOTELS}/{hotel_id}/rooms/{room['id']}")
    assert own.json()["hotel_id"] == hotel_id
    assert own.json()["price"] == ROOM["price"]


async def test_room_in_missing_hotel(admin_ac: AsyncClient):
    assert (await admin_ac.post(f"{HOTELS}/999999/rooms", json=ROOM)).status_code == 404
    resp = await admin_ac.get(
        f"{HOTELS}/999999/rooms", params={"date_from": future(1), "date_to": future(2)}
    )
    assert resp.status_code == 404


async def test_delete_room_with_bookings_is_409(
    admin_ac: AsyncClient, user_ac: AsyncClient, hotel_id: int
):
    room = (await admin_ac.post(f"{HOTELS}/{hotel_id}/rooms", json=ROOM)).json()
    booking = {"room_id": room["id"], "date_from": future(30), "date_to": future(32)}
    assert (await user_ac.post("/api/v1/bookings", json=booking)).status_code == 201
    resp = await admin_ac.delete(f"{HOTELS}/{hotel_id}/rooms/{room['id']}")
    assert resp.status_code == 409


async def test_free_rooms_listing(admin_ac: AsyncClient, user_ac: AsyncClient, hotel_id: int):
    room = (await admin_ac.post(f"{HOTELS}/{hotel_id}/rooms", json={**ROOM, "quantity": 1})).json()
    params = {"date_from": future(40), "date_to": future(45)}
    url = f"{HOTELS}/{hotel_id}/rooms"
    assert [r["id"] for r in (await admin_ac.get(url, params=params)).json()] == [room["id"]]

    booking = {"room_id": room["id"], **params}
    assert (await user_ac.post("/api/v1/bookings", json=booking)).status_code == 201
    assert (await admin_ac.get(url, params=params)).json() == []
    # День выезда свободен для следующего гостя.
    after = {"date_from": future(45), "date_to": future(47)}
    assert [r["id"] for r in (await admin_ac.get(url, params=after)).json()] == [room["id"]]
