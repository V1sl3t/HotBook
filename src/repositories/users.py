from sqlalchemy import select, update

from src.models.users import UsersOrm
from src.repositories.base import BaseRepository
from src.repositories.mappers.mappers import UserDataMapper
from src.schemas.users import UserWithHashedPassword


class UsersRepository(BaseRepository):
    model = UsersOrm
    mapper = UserDataMapper

    async def get_user_with_hashed_password(self, email: str) -> UserWithHashedPassword | None:
        query = select(UsersOrm).filter_by(email=email)
        model = (await self.session.execute(query)).scalars().one_or_none()
        if model is None:
            return None
        return UserWithHashedPassword.model_validate(model, from_attributes=True)

    async def update_password_hash(self, user_id: int, hashed_password: str) -> None:
        await self.session.execute(
            update(UsersOrm).filter_by(id=user_id).values(hashed_password=hashed_password)
        )

    async def set_admin(self, email: str, is_admin: bool = True) -> int:
        result = await self._execute_write(
            update(UsersOrm).filter_by(email=email).values(is_admin=is_admin)
        )
        return result.rowcount
