import asyncio
import logging
from pathlib import Path

from PIL import Image

from src.db import async_session_maker_null_pool
from src.schemas.bookings import Booking
from src.services.images import images_dir
from src.tasks.celery_app import celery_manager
from src.utils.db_manager import DBManager
from src.utils.email import send_email

logger = logging.getLogger(__name__)

IMAGE_WIDTHS = (1000, 500, 200)


@celery_manager.task
def resize_image(filename: str) -> list[str]:
    """Создаёт уменьшенные копии картинки; узкие картинки не растягиваются."""
    directory = images_dir()
    source = directory / Path(filename).name
    saved: list[str] = []
    with Image.open(source) as img:
        for width in IMAGE_WIDTHS:
            if img.width <= width:
                continue
            height = max(1, round(img.height * width / img.width))
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            new_name = f"{source.stem}_{width}px{source.suffix}"
            resized.save(directory / new_name, format=img.format)
            saved.append(new_name)
    logger.info("Изображение %s: созданы копии %s", source.name, saved)
    return saved


async def get_bookings_with_today_checkin() -> list[tuple[Booking, str]]:
    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        return await db.bookings.get_bookings_with_today_checkin()


@celery_manager.task(name="booking_today_checkin")
def send_emails_to_users_with_today_checkin() -> int:
    bookings = asyncio.run(get_bookings_with_today_checkin())
    for booking, email in bookings:
        send_email(
            to=email,
            subject="HotBook: сегодня заезд",
            body=(
                f"Напоминаем: сегодня заезд по брони №{booking.id} "
                f"({booking.date_from:%d.%m.%Y} — {booking.date_to:%d.%m.%Y})."
            ),
        )
    logger.info("Отправлено напоминаний о заезде: %s", len(bookings))
    return len(bookings)
