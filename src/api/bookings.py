from fastapi import APIRouter, status

from src.api.dependencies import AdminDep, DBDep, UserIdDep
from src.schemas.bookings import Booking, BookingAddRequest
from src.services.bookings import BookingService

router = APIRouter(prefix="/bookings", tags=["Бронирования"])


@router.get("", summary="Все бронирования (только для администратора)")
async def get_all_bookings(db: DBDep, _admin: AdminDep) -> list[Booking]:
    return await BookingService(db).get_all_bookings()


@router.get("/me", summary="Мои бронирования")
async def get_my_bookings(db: DBDep, user_id: UserIdDep) -> list[Booking]:
    return await BookingService(db).get_my_bookings(user_id)


@router.post("", summary="Создание брони", status_code=status.HTTP_201_CREATED)
async def create_booking(db: DBDep, user_id: UserIdDep, booking_data: BookingAddRequest) -> Booking:
    return await BookingService(db).create_booking(user_id, booking_data)
