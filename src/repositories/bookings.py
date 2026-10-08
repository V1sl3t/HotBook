from datetime import date

from sqlalchemy import select

from src.exceptions import AllRoomsAreBookedException
from src.models.bookings import BookingsOrm
from src.models.rooms import RoomsOrm
from src.models.users import UsersOrm
from src.repositories.base import BaseRepository
from src.repositories.mappers.mappers import BookingDataMapper
from src.repositories.utils import rooms_ids_for_booking
from src.schemas.bookings import Booking, BookingAdd


class BookingsRepository(BaseRepository):
    model = BookingsOrm
    mapper = BookingDataMapper

    async def get_bookings_with_today_checkin(self) -> list[tuple[Booking, str]]:
        """Брони с заездом сегодня вместе с email гостя."""
        query = (
            select(BookingsOrm, UsersOrm.email)
            .join(UsersOrm, UsersOrm.id == BookingsOrm.user_id)
            .filter(BookingsOrm.date_from == date.today())
        )
        result = await self.session.execute(query)
        return [(self.mapper.map_to_domain_entity(booking), email) for booking, email in result]

    async def add_booking(self, data: BookingAdd) -> Booking:
        # Блокируем строку номера до конца транзакции: параллельные брони того же номера
        # выстраиваются в очередь, и проверка свободных мест ниже видит уже
        # закоммиченные брони соседей. Без блокировки возможен овербукинг.
        lock_room = select(RoomsOrm.id).filter(RoomsOrm.id == data.room_id).with_for_update()
        await self.session.execute(lock_room)

        available_rooms = rooms_ids_for_booking(date_from=data.date_from, date_to=data.date_to)
        available_rooms = available_rooms.filter(RoomsOrm.id == data.room_id)
        if (await self.session.execute(available_rooms)).scalar_one_or_none() is None:
            raise AllRoomsAreBookedException
        return await self.add(data)
