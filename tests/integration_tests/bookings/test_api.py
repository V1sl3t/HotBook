import pytest
from httpx import AsyncClient

from tests.conftest import future, get_db_null_pool

API = "/api/v1/bookings"


@pytest.mark.parametrize(
    ("room_id", "date_from", "date_to", "status_code"),
    [
        # У номера 1 из моков quantity=5: шестая пересекающаяся бронь не помещается.
        (1, future(200), future(209), 201),
        (1, future(201), future(210), 201),
        (1, future(202), future(211), 201),
        (1, future(203), future(212), 201),
        (1, future(204), future(213), 201),
        (1, future(205), future(214), 409),
        # Заезд в день выезда последней брони — свободно (полуоткрытый интервал).
        (1, future(213), future(220), 201),
        (1, future(216), future(224), 201),
    ],
)
async def test_add_booking(
    room_id: int, date_from: str, date_to: str, status_code: int, user_ac: AsyncClient
):
    resp = await user_ac.post(
        API, json={"room_id": room_id, "date_from": date_from, "date_to": date_to}
    )
    assert resp.status_code == status_code, resp.text
    if status_code == 201:
        booking = resp.json()
        assert booking["room_id"] == room_id
        assert booking["price"] == 24500
        assert booking["total_cost"] > 0


@pytest.mark.parametrize(
    ("date_from", "date_to"),
    [
        (future(10), future(1)),  # выезд раньше заезда
        (future(5), future(5)),  # ноль ночей
        (future(-3), future(2)),  # заезд в прошлом
    ],
)
async def test_invalid_booking_dates_are_422(user_ac: AsyncClient, date_from: str, date_to: str):
    resp = await user_ac.post(API, json={"room_id": 1, "date_from": date_from, "date_to": date_to})
    assert resp.status_code == 422


async def test_booking_missing_room_is_404(user_ac: AsyncClient):
    resp = await user_ac.post(
        API, json={"room_id": 999999, "date_from": future(1), "date_to": future(2)}
    )
    assert resp.status_code == 404


async def test_booking_requires_auth(ac: AsyncClient):
    resp = await ac.post(API, json={"room_id": 1, "date_from": future(1), "date_to": future(2)})
    assert resp.status_code == 401
    assert (await ac.get(f"{API}/me")).status_code == 401


async def test_all_bookings_only_for_admin(
    ac: AsyncClient, user_ac: AsyncClient, admin_ac: AsyncClient
):
    assert (await ac.get(API)).status_code == 401
    assert (await user_ac.get(API)).status_code == 403
    resp = await admin_ac.get(API)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.fixture(scope="module")
async def delete_all_bookings():
    async for _db in get_db_null_pool():
        await _db.bookings.delete()
        await _db.commit()


@pytest.mark.parametrize(
    ("date_from", "date_to", "bookings_quantity"),
    [
        (future(300), future(309), 1),
        (future(301), future(310), 2),
        (future(302), future(311), 3),
    ],
)
async def test_add_and_get_my_bookings(
    date_from: str,
    date_to: str,
    bookings_quantity: int,
    user_ac: AsyncClient,
    admin_ac: AsyncClient,
    delete_all_bookings: None,
):
    resp = await user_ac.post(API, json={"room_id": 2, "date_from": date_from, "date_to": date_to})
    assert resp.status_code == 201
    # Бронь другого пользователя не видна в «моих бронях».
    await admin_ac.post(API, json={"room_id": 2, "date_from": date_from, "date_to": date_to})

    my_bookings = await user_ac.get(f"{API}/me")
    assert my_bookings.status_code == 200
    assert len(my_bookings.json()) == bookings_quantity
