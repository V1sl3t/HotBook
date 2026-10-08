from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base

if TYPE_CHECKING:
    from src.models.rooms import RoomsOrm


class ComfortsOrm(Base):
    __tablename__ = "comforts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))

    rooms: Mapped[list["RoomsOrm"]] = relationship(
        back_populates="comforts", secondary="rooms_comforts"
    )


class RoomsComfortsOrm(Base):
    __tablename__ = "rooms_comforts"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    comfort_id: Mapped[int] = mapped_column(ForeignKey("comforts.id", ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint("room_id", "comfort_id", name="uq_rooms_comforts_room_comfort"),
    )
