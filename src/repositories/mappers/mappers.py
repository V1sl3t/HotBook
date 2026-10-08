from src.models.bookings import BookingsOrm
from src.models.comforts import ComfortsOrm, RoomsComfortsOrm
from src.models.hotels import HotelsOrm
from src.models.rooms import RoomsOrm
from src.models.users import UsersOrm
from src.repositories.mappers.base import DataMapper
from src.schemas.bookings import Booking
from src.schemas.comforts import Comfort, RoomComfort
from src.schemas.hotels import Hotel
from src.schemas.rooms import Room, RoomWithRelations
from src.schemas.users import User


class HotelDataMapper(DataMapper[HotelsOrm, Hotel]):
    db_model = HotelsOrm
    schema = Hotel


class RoomDataMapper(DataMapper[RoomsOrm, Room]):
    db_model = RoomsOrm
    schema = Room


class RoomDataWithRelsMapper(DataMapper[RoomsOrm, RoomWithRelations]):
    db_model = RoomsOrm
    schema = RoomWithRelations


class UserDataMapper(DataMapper[UsersOrm, User]):
    db_model = UsersOrm
    schema = User


class BookingDataMapper(DataMapper[BookingsOrm, Booking]):
    db_model = BookingsOrm
    schema = Booking


class ComfortDataMapper(DataMapper[ComfortsOrm, Comfort]):
    db_model = ComfortsOrm
    schema = Comfort


class RoomComfortDataMapper(DataMapper[RoomsComfortsOrm, RoomComfort]):
    db_model = RoomsComfortsOrm
    schema = RoomComfort
