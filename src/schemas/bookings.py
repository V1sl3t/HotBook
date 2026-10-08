from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class BookingAddRequest(BaseModel):
    date_from: date
    date_to: date
    room_id: int

    @model_validator(mode="after")
    def check_dates(self) -> Self:
        if self.date_to <= self.date_from:
            raise ValueError("Дата выезда должна быть позже даты заезда")
        if self.date_from < date.today():
            raise ValueError("Нельзя забронировать номер на прошедшую дату")
        return self


class BookingAdd(BaseModel):
    date_from: date
    date_to: date
    room_id: int
    user_id: int
    price: int


class Booking(BookingAdd):
    id: int
    total_cost: int

    model_config = ConfigDict(from_attributes=True)
