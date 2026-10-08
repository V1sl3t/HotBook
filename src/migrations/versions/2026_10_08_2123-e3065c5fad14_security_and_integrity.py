"""security and integrity

- users.is_admin, users.created_at, bookings.created_at;
- rooms_comforts: ON DELETE CASCADE и уникальность (room_id, comfort_id);
- индексы для поиска свободных номеров и броней пользователя;
- CHECK-ограничения на даты брони, цены и количество.

Revision ID: e3065c5fad14
Revises: 7ac3d7cfdc3c
Create Date: 2026-10-08 21:23:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3065c5fad14"
down_revision: str | None = "7ac3d7cfdc3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHECK_CONSTRAINTS = (
    ("ck_bookings_dates_order", "bookings", "date_to > date_from"),
    ("ck_bookings_price_non_negative", "bookings", "price >= 0"),
    ("ck_rooms_price_non_negative", "rooms", "price >= 0"),
    ("ck_rooms_quantity_non_negative", "rooms", "quantity >= 0"),
)


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column(
        "users",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column(
        "bookings",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_index(
        "ix_bookings_room_id_dates", "bookings", ["room_id", "date_from", "date_to"], unique=False
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], unique=False)
    op.create_index("ix_rooms_hotel_id", "rooms", ["hotel_id"], unique=False)

    # Раньше дубли (room_id, comfort_id) не запрещались: оставляем по одной строке.
    op.execute(
        """
        DELETE FROM rooms_comforts a
        USING rooms_comforts b
        WHERE a.room_id = b.room_id AND a.comfort_id = b.comfort_id AND a.id > b.id
        """
    )
    op.create_unique_constraint(
        "uq_rooms_comforts_room_comfort", "rooms_comforts", ["room_id", "comfort_id"]
    )

    op.drop_constraint("rooms_comforts_room_id_fkey", "rooms_comforts", type_="foreignkey")
    op.drop_constraint("rooms_comforts_comfort_id_fkey", "rooms_comforts", type_="foreignkey")
    op.create_foreign_key(
        "rooms_comforts_room_id_fkey",
        "rooms_comforts",
        "rooms",
        ["room_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "rooms_comforts_comfort_id_fkey",
        "rooms_comforts",
        "comforts",
        ["comfort_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # NOT VALID: ограничение действует для новых и изменяемых строк, но не падает на
    # уже существующих некорректных данных (раньше API принимал бронь с date_to < date_from).
    # Проверить старые строки после чистки: ALTER TABLE ... VALIDATE CONSTRAINT ...
    for name, table, condition in CHECK_CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({condition}) NOT VALID")


def downgrade() -> None:
    for name, table, _ in reversed(CHECK_CONSTRAINTS):
        op.drop_constraint(name, table, type_="check")

    op.drop_constraint("rooms_comforts_comfort_id_fkey", "rooms_comforts", type_="foreignkey")
    op.drop_constraint("rooms_comforts_room_id_fkey", "rooms_comforts", type_="foreignkey")
    op.create_foreign_key(
        "rooms_comforts_comfort_id_fkey", "rooms_comforts", "comforts", ["comfort_id"], ["id"]
    )
    op.create_foreign_key(
        "rooms_comforts_room_id_fkey", "rooms_comforts", "rooms", ["room_id"], ["id"]
    )
    op.drop_constraint("uq_rooms_comforts_room_comfort", "rooms_comforts", type_="unique")

    op.drop_index("ix_rooms_hotel_id", table_name="rooms")
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_index("ix_bookings_room_id_dates", table_name="bookings")

    op.drop_column("bookings", "created_at")
    op.drop_column("users", "created_at")
    op.drop_column("users", "is_admin")
