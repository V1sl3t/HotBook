from collections.abc import Iterable

from sqlalchemy import delete, insert, select

from src.models.comforts import ComfortsOrm, RoomsComfortsOrm
from src.repositories.base import BaseRepository
from src.repositories.mappers.mappers import ComfortDataMapper, RoomComfortDataMapper


class ComfortsRepository(BaseRepository):
    model = ComfortsOrm
    mapper = ComfortDataMapper

    async def get_existing_ids(self, ids: Iterable[int]) -> set[int]:
        query = select(ComfortsOrm.id).filter(ComfortsOrm.id.in_(list(ids)))
        return set((await self.session.execute(query)).scalars().all())


class RoomsComfortsRepository(BaseRepository):
    model = RoomsComfortsOrm
    mapper = RoomComfortDataMapper

    async def set_room_comforts(self, room_id: int, comforts_ids: Iterable[int]) -> None:
        wanted = set(comforts_ids)
        query = select(RoomsComfortsOrm.comfort_id).filter_by(room_id=room_id)
        current = set((await self.session.execute(query)).scalars().all())

        if ids_to_delete := current - wanted:
            await self.session.execute(
                delete(RoomsComfortsOrm).filter(
                    RoomsComfortsOrm.room_id == room_id,
                    RoomsComfortsOrm.comfort_id.in_(ids_to_delete),
                )
            )
        if ids_to_insert := wanted - current:
            await self._execute_write(
                insert(RoomsComfortsOrm).values(
                    [{"room_id": room_id, "comfort_id": c_id} for c_id in sorted(ids_to_insert)]
                )
            )
