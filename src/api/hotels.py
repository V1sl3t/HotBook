from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Query, status
from fastapi.openapi.models import Example
from fastapi_cache.decorator import cache

from src.api.dependencies import AdminDep, DBDep, PaginationDep
from src.schemas.common import Page
from src.schemas.hotels import Hotel, HotelAdd, HotelPatch
from src.services.hotels import HotelService
from src.utils.cache import HOTELS_NAMESPACE

router = APIRouter(prefix="/hotels", tags=["Отели"])

HOTEL_EXAMPLES: dict[str, Example] = {
    "1": {"summary": "Крым", "value": {"title": "Черноморец", "location": "Саки, ул. Морская 7"}},
    "2": {"summary": "Дубай", "value": {"title": "Atlantis", "location": "Дубай, Palm Jumeirah"}},
}


@router.get("", summary="Поиск отелей со свободными номерами")
async def get_hotels(
    pagination: PaginationDep,
    db: DBDep,
    date_from: Annotated[date, Query(examples=["2030-08-01"])],
    date_to: Annotated[date, Query(examples=["2030-08-10"])],
    location: Annotated[str | None, Query(description="Адрес отеля", max_length=255)] = None,
    title: Annotated[str | None, Query(description="Название отеля", max_length=100)] = None,
) -> Page[Hotel]:
    return await HotelService(db).get_filtered_by_time(
        page=pagination.page,
        per_page=pagination.per_page,
        date_from=date_from,
        date_to=date_to,
        location=location,
        title=title,
    )


@router.get("/{hotel_id}", summary="Получение отеля")
@cache(expire=60, namespace=HOTELS_NAMESPACE)
async def get_hotel(hotel_id: int, db: DBDep) -> Hotel:
    return await HotelService(db).get_hotel(hotel_id)


@router.post("", summary="Создание отеля", status_code=status.HTTP_201_CREATED)
async def create_hotel(
    db: DBDep,
    _admin: AdminDep,
    hotel_data: Annotated[HotelAdd, Body(openapi_examples=HOTEL_EXAMPLES)],
) -> Hotel:
    return await HotelService(db).add_hotel(hotel_data)


@router.put("/{hotel_id}", summary="Полное обновление отеля")
async def put_hotel(db: DBDep, _admin: AdminDep, hotel_id: int, hotel_data: HotelAdd) -> Hotel:
    return await HotelService(db).edit_hotel(hotel_id, hotel_data)


@router.patch("/{hotel_id}", summary="Частичное обновление отеля")
async def patch_hotel(db: DBDep, _admin: AdminDep, hotel_id: int, hotel_data: HotelPatch) -> Hotel:
    return await HotelService(db).edit_hotel(hotel_id, hotel_data)


@router.delete("/{hotel_id}", summary="Удаление отеля", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hotel(db: DBDep, _admin: AdminDep, hotel_id: int) -> None:
    await HotelService(db).delete_hotel(hotel_id)
