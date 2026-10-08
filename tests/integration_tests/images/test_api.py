from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image

from src.config import settings

API = "/api/v1/images"


def make_png(width: int = 1200, height: int = 600) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (width, height), (255, 0, 0, 128)).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_upload_requires_admin(ac: AsyncClient, user_ac: AsyncClient):
    files = {"file": ("a.png", make_png(), "image/png")}
    assert (await ac.post(API, files=files)).status_code == 401
    assert (await user_ac.post(API, files=files)).status_code == 403


async def test_upload_ignores_client_filename(admin_ac: AsyncClient):
    files = {"file": ("../../../escaped.png", make_png(), "image/png")}
    resp = await admin_ac.post(API, files=files)
    assert resp.status_code == 201
    filename = resp.json()["filename"]
    assert "/" not in filename and ".." not in filename and filename.endswith(".png")

    images_dir = settings.MEDIA_DIR / "images"
    assert (images_dir / filename).is_file()
    assert not (settings.MEDIA_DIR.parent / "escaped.png").exists()
    # Celery в тестах работает в eager-режиме: копии создаются сразу; 1200px не растягивается.
    stem = filename.removesuffix(".png")
    assert (images_dir / f"{stem}_1000px.png").is_file()
    assert (images_dir / f"{stem}_200px.png").is_file()

    served = await admin_ac.get(resp.json()["url"])
    assert served.status_code == 200
    assert served.content == make_png()


async def test_small_image_is_not_upscaled(admin_ac: AsyncClient):
    resp = await admin_ac.post(API, files={"file": ("s.png", make_png(300, 100), "image/png")})
    stem = resp.json()["filename"].removesuffix(".png")
    images_dir = settings.MEDIA_DIR / "images"
    assert (images_dir / f"{stem}_200px.png").is_file()
    assert not (images_dir / f"{stem}_500px.png").exists()


@pytest.mark.parametrize(
    "content",
    [b"not an image at all", b"GIF89a" + b"\x00" * 100],
)
async def test_upload_rejects_non_images(admin_ac: AsyncClient, content: bytes):
    resp = await admin_ac.post(API, files={"file": ("x.png", content, "image/png")})
    assert resp.status_code == 422


async def test_upload_rejects_too_large(admin_ac: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 100)
    resp = await admin_ac.post(API, files={"file": ("big.png", make_png(), "image/png")})
    assert resp.status_code == 413
