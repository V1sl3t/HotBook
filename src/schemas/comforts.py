from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

ComfortTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class ComfortAdd(BaseModel):
    title: ComfortTitle


class Comfort(ComfortAdd):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RoomComfortAdd(BaseModel):
    room_id: int
    comfort_id: int


class RoomComfort(RoomComfortAdd):
    id: int
