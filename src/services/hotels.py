from datetime import date

from src.exceptions import HotelNotFoundException, check_date_to_after_date_from
from src.schemas.common import Page
from src.schemas.hotels import Hotel, HotelAdd, HotelPatch
from src.services.base import BaseService
from src.utils.cache import HOTELS_NAMESPACE, invalidate


class HotelService(BaseService):
    async def get_filtered_by_time(
        self,
        page: int,
        per_page: int,
        location: str | None,
        title: str | None,
        date_from: date,
        date_to: date,
    ) -> Page[Hotel]:
        check_date_to_after_date_from(date_from, date_to)
        hotels, total = await self.db.hotels.get_filtered_by_time(
            date_from=date_from,
            date_to=date_to,
            location=location,
            title=title,
            limit=per_page,
            offset=per_page * (page - 1),
        )
        return Page[Hotel](items=hotels, total=total, page=page, per_page=per_page)

    async def get_hotel(self, hotel_id: int) -> Hotel:
        hotel = await self.db.hotels.get_one_or_none(id=hotel_id)
        if hotel is None:
            raise HotelNotFoundException
        return hotel

    async def add_hotel(self, data: HotelAdd) -> Hotel:
        hotel = await self.db.hotels.add(data)
        await self.db.commit()
        return hotel

    async def edit_hotel(self, hotel_id: int, data: HotelAdd | HotelPatch) -> Hotel:
        exclude_unset = isinstance(data, HotelPatch)
        if not await self.db.hotels.edit(data, exclude_unset=exclude_unset, id=hotel_id):
            raise HotelNotFoundException
        await self.db.commit()
        await invalidate(HOTELS_NAMESPACE)
        return await self.get_hotel(hotel_id)

    async def delete_hotel(self, hotel_id: int) -> None:
        if not await self.db.hotels.delete(id=hotel_id):
            raise HotelNotFoundException
        await self.db.commit()
        await invalidate(HOTELS_NAMESPACE)
