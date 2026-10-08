import asyncio
from datetime import date, timedelta
from unittest import mock

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.cli import main as cli_main
from src.models.users import UsersOrm
from src.schemas.bookings import BookingAdd
from src.tasks import tasks
from src.utils.db_manager import DBManager
from tests.conftest import PASSWORD


async def test_health_and_ready(ac: AsyncClient):
    assert (await ac.get("/health")).json() == {"status": "ok"}
    resp = await ac.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"database": "ok", "redis": "ok"}


async def test_metrics_exposed(ac: AsyncClient):
    resp = await ac.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text


async def test_old_unversioned_routes_are_gone(ac: AsyncClient):
    assert (await ac.get("/comforts")).status_code == 404


async def test_cli_make_admin(ac: AsyncClient, db: DBManager):
    email = "cli-admin@example.com"
    await ac.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})

    # CLI сам вызывает asyncio.run, поэтому запускаем его в отдельном потоке.
    assert await asyncio.to_thread(cli_main, ["make-admin", "nobody@example.com"]) == 1
    assert await asyncio.to_thread(cli_main, ["make-admin", email]) == 0
    assert await db.session.scalar(select(UsersOrm.is_admin).filter_by(email=email)) is True
    await db.session.rollback()
    assert await asyncio.to_thread(cli_main, ["make-admin", email, "--revoke"]) == 0
    assert await db.session.scalar(select(UsersOrm.is_admin).filter_by(email=email)) is False


@pytest.mark.usefixtures("user_ac")
async def test_today_checkin_emails(db: DBManager):
    user = (await db.users.get_all())[0]
    room = (await db.rooms.get_all())[0]
    today = date.today()
    await db.bookings.add(
        BookingAdd(
            user_id=user.id,
            room_id=room.id,
            date_from=today,
            date_to=today + timedelta(days=1),
            price=1,
        )
    )
    await db.commit()

    with mock.patch.object(tasks, "send_email") as send_email:
        sent = await asyncio.to_thread(tasks.send_emails_to_users_with_today_checkin)
    assert sent >= 1
    assert user.email in {call.kwargs["to"] for call in send_email.call_args_list}
