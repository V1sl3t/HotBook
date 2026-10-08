from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func, sql
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class UsersOrm(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_admin: Mapped[bool] = mapped_column(default=False, server_default=sql.false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("email", name="users_email_key"),)
