import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.db import engine
from src.init import redis_manager

router = APIRouter(tags=["Служебное"])
logger = logging.getLogger(__name__)


@router.get("/health", summary="Liveness: процесс жив")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness: доступны БД и Redis")
async def ready() -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception("Readiness: БД недоступна")
        checks["database"] = "error"
    try:
        await redis_manager.ping()
        checks["redis"] = "ok"
    except Exception:
        logger.exception("Readiness: Redis недоступен")
        checks["redis"] = "error"
    is_ready = all(value == "ok" for value in checks.values())
    return JSONResponse(status_code=200 if is_ready else 503, content=checks)
