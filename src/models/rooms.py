from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base

if TYPE_CHECKING:
    from src.models.comforts import ComfortsOrm


class RoomsOrm(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id"), index=True)
    title: Mapped[str]
    description: Mapped[str | None]
    price: Mapped[int]
    quantity: Mapped[int]

    comforts: Mapped[list["ComfortsOrm"]] = relationship(
        back_populates="rooms", secondary="rooms_comforts"
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_rooms_price_non_negative"),
        CheckConstraint("quantity >= 0", name="ck_rooms_quantity_non_negative"),
    )
