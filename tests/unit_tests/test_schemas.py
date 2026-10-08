from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from src.schemas.bookings import BookingAddRequest
from src.schemas.hotels import HotelAdd
from src.schemas.rooms import RoomAddRequest
from src.schemas.users import UserRegister

TODAY = date.today()


@pytest.mark.parametrize(
    ("date_from", "date_to"),
    [
        (TODAY + timedelta(days=10), TODAY + timedelta(days=1)),  # выезд раньше заезда
        (TODAY + timedelta(days=5), TODAY + timedelta(days=5)),  # ноль ночей
        (TODAY - timedelta(days=1), TODAY + timedelta(days=5)),  # заезд в прошлом
    ],
)
def test_booking_dates_validation(date_from: date, date_to: date):
    with pytest.raises(ValidationError):
        BookingAddRequest(room_id=1, date_from=date_from, date_to=date_to)


def test_booking_today_is_allowed():
    BookingAddRequest(room_id=1, date_from=TODAY, date_to=TODAY + timedelta(days=1))


@pytest.mark.parametrize(
    "data",
    [
        {"title": "x" * 101, "location": "Сочи"},
        {"title": "   ", "location": "Сочи"},
        {"title": "Отель", "location": ""},
    ],
)
def test_hotel_validation(data: dict):
    with pytest.raises(ValidationError):
        HotelAdd.model_validate(data)


@pytest.mark.parametrize(
    "data",
    [
        {"title": "Номер", "price": -1, "quantity": 1},
        {"title": "Номер", "price": 100, "quantity": 0},
    ],
)
def test_room_validation(data: dict):
    with pytest.raises(ValidationError):
        RoomAddRequest.model_validate(data)


def test_register_requires_long_password():
    with pytest.raises(ValidationError):
        UserRegister(email="a@b.ru", password="1234567")
