from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.exceptions import RoomNotFoundException
from src.models.rooms import RoomsOrm
from src.repositories.base import BaseRepository
from src.repositories.mappers.mappers import RoomDataMapper, RoomDataWithRelsMapper
from src.repositories.utils import rooms_ids_for_booking
from src.schemas.rooms import RoomWithRelations


class RoomsRepository(BaseRepository):
    model = RoomsOrm
    mapper = RoomDataMapper

    async def get_filtered_by_time(
        self, hotel_id: int, date_from: date, date_to: date
    ) -> list[RoomWithRelations]:
        rooms_ids_to_get = rooms_ids_for_booking(date_from, date_to, hotel_id)
        query = (
            select(RoomsOrm)
            .options(selectinload(RoomsOrm.comforts))
            .filter(RoomsOrm.id.in_(rooms_ids_to_get))
            .order_by(RoomsOrm.id)
        )
        result = await self.session.execute(query)
        return [
            RoomDataWithRelsMapper.map_to_domain_entity(model) for model in result.scalars().all()
        ]

    async def get_one_with_rels(self, **filter_by: Any) -> RoomWithRelations:
        query = select(RoomsOrm).options(selectinload(RoomsOrm.comforts)).filter_by(**filter_by)
        # populate_existing: связи могли поменяться в этой же сессии после первой загрузки.
        query = query.execution_options(populate_existing=True)
        model = (await self.session.execute(query)).scalar_one_or_none()
        if model is None:
            raise RoomNotFoundException
        return RoomDataWithRelsMapper.map_to_domain_entity(model)
