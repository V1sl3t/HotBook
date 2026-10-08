import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.auth import router as router_auth
from src.api.bookings import router as router_bookings
from src.api.comforts import router as router_comforts
from src.api.health import router as router_health
from src.api.hotels import router as router_hotels
from src.api.images import router as router_images
from src.api.rooms import router as router_rooms
from src.config import settings
from src.db import engine
from src.exceptions import HotBookException
from src.init import redis_manager
from src.utils.cache import request_key_builder

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.MODE, send_default_pii=False)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await redis_manager.connect()
    FastAPICache.init(
        RedisBackend(redis_manager.client),
        prefix="fastapi-cache",
        key_builder=request_key_builder,
    )
    logger.info("FastAPI cache initialized")
    yield
    await redis_manager.close()
    await engine.dispose()


app = FastAPI(
    title="HotBook",
    description="Сервис бронирования номеров в отелях",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HotBookException)
async def hotbook_exception_handler(request: Request, exc: HotBookException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

api_v1 = APIRouter(prefix="/api/v1")
for router in (
    router_auth,
    router_hotels,
    router_rooms,
    router_bookings,
    router_comforts,
    router_images,
):
    api_v1.include_router(router)

app.include_router(api_v1)
app.include_router(router_health)

settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

Instrumentator(excluded_handlers=["/health", "/ready", "/metrics"]).instrument(app).expose(
    app, include_in_schema=False
)
