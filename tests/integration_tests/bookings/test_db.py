import asyncio
from datetime import date, timedelta

import pytest

from src.db import async_session_maker_null_pool
from src.exceptions import AllRoomsAreBookedException
from src.schemas.bookings import Booking, BookingAdd
from src.schemas.hotels import HotelAdd
from src.schemas.rooms import RoomAdd
from src.utils.db_manager import DBManager


@pytest.mark.usefixtures("user_ac")
async def test_booking_crud(db: DBManager):
    user_id = (await db.users.get_all())[0].id
    room_id = (await db.rooms.get_all())[0].id
    booking_data = BookingAdd(
        user_id=user_id,
        room_id=room_id,
        date_from=date(2031, 8, 10),
        date_to=date(2031, 8, 20),
        price=100,
    )
    new_booking: Booking = await db.bookings.add(booking_data)
    booking = await db.bookings.get_one_or_none(id=new_booking.id)
    assert booking
    assert booking.model_dump(exclude={"id", "total_cost"}) == booking_data.model_dump()
    assert booking.total_cost == 100 * 10

    updated = booking_data.model_copy(update={"date_to": date(2031, 8, 25)})
    assert await db.bookings.edit(updated, id=new_booking.id) == 1
    assert (await db.bookings.get_one(id=new_booking.id)).date_to == date(2031, 8, 25)

    assert await db.bookings.delete(id=new_booking.id) == 1
    assert await db.bookings.get_one_or_none(id=new_booking.id) is None
    assert await db.bookings.delete(id=new_booking.id) == 0


@pytest.mark.usefixtures("user_ac")
async def test_parallel_bookings_cannot_overbook():
    """Вторая транзакция ждёт блокировку номера и видит бронь первой.

    Без SELECT ... FOR UPDATE вторая транзакция не блокируется, не видит
    незакоммиченную бронь первой и тоже бронирует последний номер.
    """
    async with DBManager(session_factory=async_session_maker_null_pool) as setup:
        hotel = await setup.hotels.add(HotelAdd(title="Гонка", location="Тест"))
        room = await setup.rooms.add(
            RoomAdd(hotel_id=hotel.id, title="Последний", price=100, quantity=1)
        )
        user_id = (await setup.users.get_all())[0].id
        await setup.commit()

    start = date.today() + timedelta(days=500)
    data = BookingAdd(
        user_id=user_id,
        room_id=room.id,
        date_from=start,
        date_to=start + timedelta(days=3),
        price=100,
    )
    async with (
        DBManager(session_factory=async_session_maker_null_pool) as first,
        DBManager(session_factory=async_session_maker_null_pool) as second,
    ):
        await first.bookings.add_booking(data)  # держит блокировку, ещё не закоммичено
        competing = asyncio.create_task(second.bookings.add_booking(data))
        await asyncio.sleep(0.5)
        assert not competing.done(), "вторая бронь не ждала блокировку номера"

        await first.commit()
        with pytest.raises(AllRoomsAreBookedException):
            await competing
