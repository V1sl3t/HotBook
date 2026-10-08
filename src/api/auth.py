from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response, status

from src.api.dependencies import CurrentUserDep, DBDep
from src.config import settings
from src.exceptions import IncorrectTokenException
from src.schemas.users import TokenResponse, User, UserLogin, UserRegister
from src.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Аутентификация и авторизация"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = {"httponly": True, "secure": settings.COOKIE_SECURE, "samesite": "lax"}
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,  # ty: ignore[invalid-argument-type]
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        **common,  # ty: ignore[invalid-argument-type]
    )


@router.post("/register", summary="Регистрация", status_code=status.HTTP_201_CREATED)
async def register_user(db: DBDep, data: UserRegister) -> User:
    return await AuthService(db).register_user(data)


@router.post("/login", summary="Вход")
async def login_user(
    db: DBDep, data: UserLogin, request: Request, response: Response
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    access_token, refresh_token = await AuthService(db).login_user(data, client_ip=client_ip)
    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", summary="Обновление пары токенов по refresh-токену")
async def refresh_tokens(
    response: Response,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse:
    if not refresh_token:
        raise IncorrectTokenException
    access_token, new_refresh_token = await AuthService().refresh_tokens(refresh_token)
    _set_auth_cookies(response, access_token, new_refresh_token)
    return TokenResponse(access_token=access_token)


@router.get("/me", summary="Текущий пользователь")
async def get_me(user: CurrentUserDep) -> User:
    return user


@router.post("/logout", summary="Выход", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    response: Response,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> None:
    await AuthService().revoke_refresh_token(refresh_token)
    response.delete_cookie(ACCESS_COOKIE, httponly=True, secure=settings.COOKIE_SECURE)
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True, secure=settings.COOKIE_SECURE
    )
