from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Query, status
from fastapi.openapi.models import Example

from src.api.dependencies import AdminDep, DBDep
from src.schemas.rooms import RoomAddRequest, RoomPatchRequest, RoomWithRelations
from src.services.rooms import RoomService

router = APIRouter(prefix="/hotels", tags=["Номера"])

ROOM_EXAMPLES: dict[str, Example] = {
    "1": {
        "summary": "Стандарт",
        "value": {"title": "Стандарт", "description": "Вид на море", "price": 5000, "quantity": 5},
    },
    "2": {
        "summary": "Люкс с удобствами",
        "value": {"title": "Люкс", "price": 12000, "quantity": 2, "comforts_ids": [1]},
    },
}


@router.get("/{hotel_id}/rooms", summary="Свободные номера отеля на даты")
async def get_rooms(
    hotel_id: int,
    db: DBDep,
    date_from: Annotated[date, Query(examples=["2030-08-01"])],
    date_to: Annotated[date, Query(examples=["2030-08-10"])],
) -> list[RoomWithRelations]:
    return await RoomService(db).get_filtered_by_time(
        hotel_id=hotel_id, date_from=date_from, date_to=date_to
    )


@router.get("/{hotel_id}/rooms/{room_id}", summary="Получение номера")
async def get_room(db: DBDep, hotel_id: int, room_id: int) -> RoomWithRelations:
    return await RoomService(db).get_room(hotel_id=hotel_id, room_id=room_id)


@router.post("/{hotel_id}/rooms", summary="Создание номера", status_code=status.HTTP_201_CREATED)
async def create_room(
    db: DBDep,
    _admin: AdminDep,
    hotel_id: int,
    room_data: Annotated[RoomAddRequest, Body(openapi_examples=ROOM_EXAMPLES)],
) -> RoomWithRelations:
    return await RoomService(db).create_room(hotel_id, room_data)


@router.put("/{hotel_id}/rooms/{room_id}", summary="Полное обновление номера")
async def put_room(
    db: DBDep, _admin: AdminDep, hotel_id: int, room_id: int, room_data: RoomAddRequest
) -> RoomWithRelations:
    return await RoomService(db).edit_room(hotel_id, room_id, room_data)


@router.patch("/{hotel_id}/rooms/{room_id}", summary="Частичное обновление номера")
async def patch_room(
    db: DBDep, _admin: AdminDep, hotel_id: int, room_id: int, room_data: RoomPatchRequest
) -> RoomWithRelations:
    return await RoomService(db).edit_room(hotel_id, room_id, room_data)


@router.delete(
    "/{hotel_id}/rooms/{room_id}",
    summary="Удаление номера",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_room(db: DBDep, _admin: AdminDep, hotel_id: int, room_id: int) -> None:
    await RoomService(db).delete_room(hotel_id, room_id)
