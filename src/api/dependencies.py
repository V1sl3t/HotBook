from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Query, Security
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.db import async_session_maker
from src.exceptions import (
    IncorrectTokenException,
    NoAccessTokenException,
    PermissionDeniedException,
)
from src.schemas.users import User
from src.services.auth import AuthService
from src.utils.db_manager import DBManager


class PaginationParams(BaseModel):
    page: int
    per_page: int


def get_pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PaginationParams:
    return PaginationParams(page=page, per_page=per_page)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]


async def get_db() -> AsyncGenerator[DBManager]:
    async with DBManager(session_factory=async_session_maker) as db:
        yield db


DBDep = Annotated[DBManager, Depends(get_db)]

cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def get_token(
    cookie_token: Annotated[str | None, Security(cookie_scheme)],
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
) -> str:
    """Access-токен из заголовка ``Authorization: Bearer`` или из httpOnly-cookie."""
    if bearer is not None:
        return bearer.credentials
    if cookie_token:
        return cookie_token
    raise NoAccessTokenException


def get_current_user_id(token: Annotated[str, Depends(get_token)]) -> int:
    return AuthService.decode_token(token)["user_id"]


UserIdDep = Annotated[int, Depends(get_current_user_id)]


async def get_current_user(db: DBDep, user_id: UserIdDep) -> User:
    user = await db.users.get_one_or_none(id=user_id)
    if user is None:
        # Токен подписан нами, но пользователя уже нет.
        raise IncorrectTokenException
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUserDep) -> User:
    if not user.is_admin:
        raise PermissionDeniedException
    return user


AdminDep = Annotated[User, Depends(get_current_admin)]
