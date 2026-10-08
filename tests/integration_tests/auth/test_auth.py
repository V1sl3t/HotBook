from datetime import UTC, datetime, timedelta

import jwt
from httpx import AsyncClient
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import insert, select

from src.config import settings
from src.models.users import UsersOrm
from src.utils.db_manager import DBManager
from tests.conftest import PASSWORD, make_client

API = "/api/v1/auth"


async def test_register_login_me_logout_flow(ac: AsyncClient):
    email = "flow@example.com"
    resp = await ac.post(f"{API}/register", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 201
    assert resp.json()["email"] == email
    assert "hashed_password" not in resp.json()

    resp = await ac.post(f"{API}/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    set_cookie = resp.headers.get_list("set-cookie")
    access_cookie = next(c for c in set_cookie if c.startswith("access_token="))
    refresh_cookie = next(c for c in set_cookie if c.startswith("refresh_token="))
    assert "HttpOnly" in access_cookie and "samesite=lax" in access_cookie.lower()
    assert "HttpOnly" in refresh_cookie and "Path=/api/v1/auth" in refresh_cookie

    me = await ac.get(f"{API}/me")
    assert me.status_code == 200
    assert me.json() == {"id": me.json()["id"], "email": email, "is_admin": False}

    assert (await ac.post(f"{API}/logout")).status_code == 204
    assert "access_token" not in ac.cookies
    assert (await ac.get(f"{API}/me")).status_code == 401


async def test_bearer_header_is_accepted(ac: AsyncClient):
    email = "bearer@example.com"
    await ac.post(f"{API}/register", json={"email": email, "password": PASSWORD})
    async with make_client() as other:
        token = await other.post(f"{API}/login", json={"email": email, "password": PASSWORD})
        access_token = token.json()["access_token"]
    resp = await ac.get(f"{API}/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == email


async def test_register_duplicate_and_short_password(ac: AsyncClient):
    data = {"email": "dup@example.com", "password": PASSWORD}
    assert (await ac.post(f"{API}/register", json=data)).status_code == 201
    assert (await ac.post(f"{API}/register", json=data)).status_code == 409
    short = {"email": "short@example.com", "password": "1"}
    assert (await ac.post(f"{API}/register", json=short)).status_code == 422


async def test_login_unknown_email_and_wrong_password_look_the_same(ac: AsyncClient):
    await ac.post(f"{API}/register", json={"email": "known@example.com", "password": PASSWORD})
    unknown = await ac.post(f"{API}/login", json={"email": "nobody@example.com", "password": "x"})
    wrong = await ac.post(f"{API}/login", json={"email": "known@example.com", "password": "x"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "Неверный email или пароль"}


async def test_login_rate_limit(ac: AsyncClient):
    email = "bruteforce@example.com"
    await ac.post(f"{API}/register", json={"email": email, "password": PASSWORD})
    for _ in range(settings.LOGIN_RATE_LIMIT_ATTEMPTS):
        resp = await ac.post(f"{API}/login", json={"email": email, "password": "wrong"})
        assert resp.status_code == 401
    # Даже правильный пароль не принимается, пока не истечёт окно.
    resp = await ac.post(f"{API}/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 429


async def test_invalid_tokens_give_401_not_500(ac: AsyncClient):
    expired = jwt.encode(
        {"user_id": 1, "type": "access", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    for token in (expired, "garbage"):
        ac.cookies.set("access_token", token)
        assert (await ac.get(f"{API}/me")).status_code == 401
        resp = await ac.get(f"{API}/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    ac.cookies.clear()
    assert (await ac.get(f"{API}/me")).status_code == 401


async def test_token_of_deleted_user_is_rejected(ac: AsyncClient):
    token = jwt.encode(
        {"user_id": 999_999, "type": "access", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    resp = await ac.get(f"{API}/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_refresh_rotates_and_old_refresh_token_is_single_use(ac: AsyncClient):
    email = "refresh@example.com"
    await ac.post(f"{API}/register", json={"email": email, "password": PASSWORD})
    await ac.post(f"{API}/login", json={"email": email, "password": PASSWORD})
    old_refresh = ac.cookies["refresh_token"]

    resp = await ac.post(f"{API}/refresh")
    assert resp.status_code == 200
    assert ac.cookies["refresh_token"] != old_refresh
    assert (await ac.get(f"{API}/me")).json()["email"] == email

    async with make_client() as attacker:
        attacker.cookies.set("refresh_token", old_refresh, path="/api/v1/auth")
        assert (await attacker.post(f"{API}/refresh")).status_code == 401


async def test_logout_revokes_refresh_token(ac: AsyncClient):
    email = "logout@example.com"
    await ac.post(f"{API}/register", json={"email": email, "password": PASSWORD})
    await ac.post(f"{API}/login", json={"email": email, "password": PASSWORD})
    refresh = ac.cookies["refresh_token"]
    await ac.post(f"{API}/logout")
    async with make_client() as other:
        other.cookies.set("refresh_token", refresh, path="/api/v1/auth")
        assert (await other.post(f"{API}/refresh")).status_code == 401


async def test_refresh_without_cookie(ac: AsyncClient):
    assert (await ac.post(f"{API}/refresh")).status_code == 401


async def test_legacy_bcrypt_password_is_rehashed_on_login(ac: AsyncClient, db: DBManager):
    email = "legacy@example.com"
    legacy_hash = PasswordHash((BcryptHasher(),)).hash(PASSWORD)
    await db.session.execute(insert(UsersOrm).values(email=email, hashed_password=legacy_hash))
    await db.commit()

    resp = await ac.post(f"{API}/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200
    stored = await db.session.scalar(select(UsersOrm.hashed_password).filter_by(email=email))
    assert stored is not None and stored.startswith("$argon2")
