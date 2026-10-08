from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.schemas.comforts import Comfort

RoomTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
RoomDescription = Annotated[str, StringConstraints(max_length=2000)]
Price = Annotated[int, Field(ge=0)]
Quantity = Annotated[int, Field(ge=1)]


class RoomAddRequest(BaseModel):
    title: RoomTitle
    description: RoomDescription | None = None
    price: Price
    quantity: Quantity
    comforts_ids: list[int] = []


class RoomAdd(BaseModel):
    hotel_id: int
    title: RoomTitle
    description: RoomDescription | None = None
    price: Price
    quantity: Quantity


class Room(RoomAdd):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RoomWithRelations(Room):
    comforts: list[Comfort]


class RoomPatchRequest(BaseModel):
    title: RoomTitle | None = None
    description: RoomDescription | None = None
    price: Price | None = None
    quantity: Quantity | None = None
    comforts_ids: list[int] | None = None


class RoomPatch(BaseModel):
    title: RoomTitle | None = None
    description: RoomDescription | None = None
    price: Price | None = None
    quantity: Quantity | None = None
