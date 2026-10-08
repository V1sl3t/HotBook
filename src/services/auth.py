import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from src.config import settings
from src.exceptions import (
    IncorrectTokenException,
    InvalidCredentialsException,
    ObjectAlreadyExistsException,
    TooManyRequestsException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from src.init import redis_manager
from src.schemas.users import User, UserAdd, UserLogin, UserRegister
from src.services.base import BaseService

TokenType = Literal["access", "refresh"]

# Новые пароли хешируются Argon2; bcrypt нужен для проверки хешей, созданных до миграции.
password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

# Хеш для выравнивания времени ответа, когда пользователя нет:
# иначе по скорости ответа можно узнать, зарегистрирован ли email.
_DUMMY_HASH = password_hash.hash(uuid.uuid4().hex)

REFRESH_KEY_PREFIX = "refresh_token"
LOGIN_ATTEMPTS_KEY_PREFIX = "login_attempts"


class AuthService(BaseService):
    @staticmethod
    def hash_password(password: str) -> str:
        return password_hash.hash(password)

    @staticmethod
    def _encode(user_id: int, token_type: TokenType, expires_in: timedelta, **extra: Any) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "user_id": user_id,
            "type": token_type,
            "iat": now,
            "exp": now + expires_in,
            **extra,
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_access_token(self, user_id: int) -> str:
        return self._encode(
            user_id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

    async def create_refresh_token(self, user_id: int) -> str:
        jti = uuid.uuid4().hex
        ttl = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await redis_manager.set(
            f"{REFRESH_KEY_PREFIX}:{jti}", str(user_id), expire=int(ttl.total_seconds())
        )
        return self._encode(user_id, "refresh", ttl, jti=jti)

    @staticmethod
    def decode_token(token: str, expected_type: TokenType = "access") -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"require": ["exp", "user_id", "type"]},
            )
        except jwt.InvalidTokenError as ex:
            raise IncorrectTokenException from ex
        if payload["type"] != expected_type or not isinstance(payload["user_id"], int):
            raise IncorrectTokenException
        return payload

    async def register_user(self, data: UserRegister) -> User:
        new_user_data = UserAdd(email=data.email, hashed_password=self.hash_password(data.password))
        try:
            user = await self.db.users.add(new_user_data)
        except ObjectAlreadyExistsException as ex:
            raise UserAlreadyExistsException from ex
        await self.db.commit()
        return user

    async def login_user(self, data: UserLogin, client_ip: str) -> tuple[str, str]:
        attempts_key = f"{LOGIN_ATTEMPTS_KEY_PREFIX}:{client_ip}:{data.email.lower()}"
        attempts = await redis_manager.get(attempts_key)
        if attempts is not None and int(attempts) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
            raise TooManyRequestsException

        user = await self.db.users.get_user_with_hashed_password(email=data.email)
        if user is None:
            password_hash.verify(data.password, _DUMMY_HASH)
            is_valid, new_hash = False, None
        else:
            is_valid, new_hash = password_hash.verify_and_update(
                data.password, user.hashed_password
            )

        if user is None or not is_valid:
            await redis_manager.incr_with_expire(
                attempts_key, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
            )
            raise InvalidCredentialsException

        await redis_manager.delete(attempts_key)
        if new_hash is not None:
            # Старый bcrypt-хеш прозрачно заменяется на Argon2 при успешном входе.
            await self.db.users.update_password_hash(user.id, new_hash)
            await self.db.commit()
        return self.create_access_token(user.id), await self.create_refresh_token(user.id)

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        payload = self.decode_token(refresh_token, expected_type="refresh")
        # getdel: refresh-токен одноразовый, повторное использование отклоняется.
        stored = await redis_manager.getdel(f"{REFRESH_KEY_PREFIX}:{payload.get('jti')}")
        if stored is None or int(stored) != payload["user_id"]:
            raise IncorrectTokenException
        user_id = payload["user_id"]
        return self.create_access_token(user_id), await self.create_refresh_token(user_id)

    async def revoke_refresh_token(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = self.decode_token(refresh_token, expected_type="refresh")
        except IncorrectTokenException:
            return
        await redis_manager.delete(f"{REFRESH_KEY_PREFIX}:{payload.get('jti')}")

    async def get_me(self, user_id: int) -> User:
        user = await self.db.users.get_one_or_none(id=user_id)
        if user is None:
            raise UserNotFoundException
        return user
