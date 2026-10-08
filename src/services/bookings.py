from src.exceptions import RoomNotFoundException
from src.schemas.bookings import Booking, BookingAdd, BookingAddRequest
from src.services.base import BaseService


class BookingService(BaseService):
    async def get_all_bookings(self) -> list[Booking]:
        return await self.db.bookings.get_all()

    async def get_my_bookings(self, user_id: int) -> list[Booking]:
        return await self.db.bookings.get_filtered(user_id=user_id)

    async def create_booking(self, user_id: int, booking_data: BookingAddRequest) -> Booking:
        room = await self.db.rooms.get_one_or_none(id=booking_data.room_id)
        if room is None:
            raise RoomNotFoundException
        new_booking_data = BookingAdd(
            price=room.price, user_id=user_id, **booking_data.model_dump()
        )
        booking = await self.db.bookings.add_booking(new_booking_data)
        await self.db.commit()
        return booking
