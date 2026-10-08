from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

HotelTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
HotelLocation = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


class HotelAdd(BaseModel):
    title: HotelTitle
    location: HotelLocation


class Hotel(HotelAdd):
    id: int

    model_config = ConfigDict(from_attributes=True)


class HotelPatch(BaseModel):
    title: HotelTitle | None = Field(default=None)
    location: HotelLocation | None = Field(default=None)
