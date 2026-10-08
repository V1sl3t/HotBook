from datetime import date

from sqlalchemy import Select, func, select

from src.models.bookings import BookingsOrm
from src.models.rooms import RoomsOrm


def rooms_ids_for_booking(
    date_from: date,
    date_to: date,
    hotel_id: int | None = None,
) -> Select[int]:
    """Запрос id номеров, у которых в периоде [date_from, date_to) есть свободные места.

    Период брони полуоткрытый: день выезда одного гостя может быть днём заезда другого.
    """
    rooms_count = (
        select(BookingsOrm.room_id, func.count().label("rooms_booked"))
        .filter(
            BookingsOrm.date_from < date_to,
            BookingsOrm.date_to > date_from,
        )
        .group_by(BookingsOrm.room_id)
        .cte(name="rooms_count")
    )
    rooms_ids_to_get = (
        select(RoomsOrm.id)
        .outerjoin(rooms_count, RoomsOrm.id == rooms_count.c.room_id)
        .filter(RoomsOrm.quantity - func.coalesce(rooms_count.c.rooms_booked, 0) > 0)
    )
    if hotel_id is not None:
        rooms_ids_to_get = rooms_ids_to_get.filter(RoomsOrm.hotel_id == hotel_id)
    return rooms_ids_to_get
