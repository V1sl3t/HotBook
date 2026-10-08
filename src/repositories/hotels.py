from datetime import date

from sqlalchemy import Select, func, select

from src.models.hotels import HotelsOrm
from src.models.rooms import RoomsOrm
from src.repositories.base import BaseRepository
from src.repositories.mappers.mappers import HotelDataMapper
from src.repositories.utils import rooms_ids_for_booking
from src.schemas.hotels import Hotel


class HotelsRepository(BaseRepository):
    model = HotelsOrm
    mapper = HotelDataMapper

    @staticmethod
    def _filtered_by_time_query(
        date_from: date, date_to: date, location: str | None, title: str | None
    ) -> Select[HotelsOrm]:
        rooms_ids_to_get = rooms_ids_for_booking(date_from=date_from, date_to=date_to)
        hotels_ids_to_get = select(RoomsOrm.hotel_id).filter(RoomsOrm.id.in_(rooms_ids_to_get))
        query = select(HotelsOrm).filter(HotelsOrm.id.in_(hotels_ids_to_get))
        if location:
            query = query.filter(func.lower(HotelsOrm.location).contains(location.strip().lower()))
        if title:
            query = query.filter(func.lower(HotelsOrm.title).contains(title.strip().lower()))
        return query

    async def get_filtered_by_time(
        self,
        date_from: date,
        date_to: date,
        location: str | None,
        title: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Hotel], int]:
        query = self._filtered_by_time_query(date_from, date_to, location, title)
        total = (
            await self.session.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()
        result = await self.session.execute(
            query.order_by(HotelsOrm.id).limit(limit).offset(offset)
        )
        hotels = [self.mapper.map_to_domain_entity(hotel) for hotel in result.scalars().all()]
        return hotels, total
