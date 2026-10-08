import logging
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from fastapi_cache import FastAPICache
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

COMFORTS_NAMESPACE = "comforts"
HOTELS_NAMESPACE = "hotels"


def request_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Request | None = None,
    response: Response | None = None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """Ключ кэша по пути и query-параметрам запроса.

    Стандартный key builder fastapi-cache включает в ключ все аргументы эндпоинта,
    в том числе объект сессии БД, который новый на каждый запрос, поэтому кэш никогда
    не срабатывал.
    """
    if request is None:
        return f"{namespace}:{func.__module__}:{getattr(func, '__qualname__', func)}"
    query = urlencode(sorted(request.query_params.multi_items()))
    return f"{namespace}:{request.url.path}?{query}"


async def invalidate(namespace: str) -> None:
    """Сбрасывает кэш namespace после изменения данных."""
    try:
        await FastAPICache.clear(namespace=namespace)
    except AssertionError:
        # Кэш не инициализирован (CLI, Celery) — сбрасывать нечего.
        pass
    except Exception:
        logger.exception("Не удалось сбросить кэш namespace=%s", namespace)
