from datetime import date

from src.exceptions import RoomNotFoundException, check_date_to_after_date_from
from src.schemas.rooms import (
    Room,
    RoomAdd,
    RoomAddRequest,
    RoomPatch,
    RoomPatchRequest,
    RoomWithRelations,
)
from src.services.base import BaseService
from src.services.comforts import ComfortService
from src.services.hotels import HotelService


class RoomService(BaseService):
    async def get_filtered_by_time(
        self, hotel_id: int, date_from: date, date_to: date
    ) -> list[RoomWithRelations]:
        check_date_to_after_date_from(date_from, date_to)
        await HotelService(self.db).get_hotel(hotel_id)
        return await self.db.rooms.get_filtered_by_time(
            hotel_id=hotel_id, date_from=date_from, date_to=date_to
        )

    async def get_room(self, hotel_id: int, room_id: int) -> RoomWithRelations:
        return await self.db.rooms.get_one_with_rels(id=room_id, hotel_id=hotel_id)

    async def create_room(self, hotel_id: int, room_data: RoomAddRequest) -> RoomWithRelations:
        await HotelService(self.db).get_hotel(hotel_id)
        await ComfortService(self.db).check_comforts_exist(room_data.comforts_ids)
        _room_data = RoomAdd(hotel_id=hotel_id, **room_data.model_dump(exclude={"comforts_ids"}))
        room: Room = await self.db.rooms.add(_room_data)
        await self.db.rooms_comforts.set_room_comforts(room.id, room_data.comforts_ids)
        await self.db.commit()
        return await self.get_room(hotel_id, room.id)

    async def edit_room(
        self, hotel_id: int, room_id: int, room_data: RoomAddRequest | RoomPatchRequest
    ) -> RoomWithRelations:
        await self.get_room_with_check(hotel_id, room_id)
        if room_data.comforts_ids is not None:
            await ComfortService(self.db).check_comforts_exist(room_data.comforts_ids)

        partial = isinstance(room_data, RoomPatchRequest)
        fields = room_data.model_dump(exclude={"comforts_ids"}, exclude_unset=partial)
        # hotel_id берётся только из URL: номер нельзя перенести в другой отель.
        await self.db.rooms.edit(
            RoomPatch.model_validate(fields), exclude_unset=True, id=room_id, hotel_id=hotel_id
        )
        if room_data.comforts_ids is not None:
            await self.db.rooms_comforts.set_room_comforts(room_id, room_data.comforts_ids)
        await self.db.commit()
        return await self.get_room(hotel_id, room_id)

    async def delete_room(self, hotel_id: int, room_id: int) -> None:
        await self.get_room_with_check(hotel_id, room_id)
        await self.db.rooms.delete(id=room_id, hotel_id=hotel_id)
        await self.db.commit()

    async def get_room_with_check(self, hotel_id: int, room_id: int) -> Room:
        await HotelService(self.db).get_hotel(hotel_id)
        room = await self.db.rooms.get_one_or_none(id=room_id, hotel_id=hotel_id)
        if room is None:
            raise RoomNotFoundException
        return room
