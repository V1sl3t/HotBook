from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from src.config import settings
from src.exceptions import IncorrectTokenException
from src.services.auth import AuthService, password_hash


def test_access_token_roundtrip():
    token = AuthService().create_access_token(user_id=1)
    payload = AuthService.decode_token(token)
    assert payload["user_id"] == 1
    assert payload["type"] == "access"


def _encode(**claims) -> str:
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("garbage", id="garbage"),
        pytest.param(
            _encode(user_id=1, type="access", exp=datetime.now(UTC) - timedelta(minutes=1)),
            id="expired",
        ),
        pytest.param(_encode(user_id=1, type="access"), id="no-exp"),
        pytest.param(
            _encode(type="access", exp=datetime.now(UTC) + timedelta(minutes=5)), id="no-user"
        ),
        pytest.param(
            _encode(user_id=1, type="refresh", exp=datetime.now(UTC) + timedelta(minutes=5)),
            id="refresh-as-access",
        ),
        pytest.param(
            jwt.encode(
                {"user_id": 1, "type": "access", "exp": datetime.now(UTC) + timedelta(minutes=5)},
                "another-secret-key-that-is-long-enough",
                algorithm="HS256",
            ),
            id="wrong-signature",
        ),
    ],
)
def test_decode_rejects_invalid_tokens(token: str):
    with pytest.raises(IncorrectTokenException):
        AuthService.decode_token(token)


def test_new_passwords_use_argon2_and_bcrypt_is_upgraded():
    assert AuthService.hash_password("secret-password").startswith("$argon2")

    legacy_hash = PasswordHash((BcryptHasher(),)).hash("secret-password")
    is_valid, new_hash = password_hash.verify_and_update("secret-password", legacy_hash)
    assert is_valid
    assert new_hash is not None and new_hash.startswith("$argon2")
