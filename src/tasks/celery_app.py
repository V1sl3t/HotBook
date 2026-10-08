from celery import Celery
from celery.schedules import crontab

from src.config import settings

celery_manager = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    include=["src.tasks.tasks"],
)

celery_manager.conf.update(
    timezone="Europe/Moscow",
    task_always_eager=settings.MODE == "TEST",
    beat_schedule={
        "send-today-checkin-emails": {
            "task": "booking_today_checkin",
            "schedule": crontab(hour=9, minute=0),
        }
    },
)
