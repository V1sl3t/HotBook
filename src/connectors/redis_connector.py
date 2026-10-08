import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._redis: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis не подключён: сначала вызовите connect()")
        return self._redis

    async def connect(self) -> None:
        logger.info("Подключение к Redis host=%s, port=%s", self.host, self.port)
        self._redis = redis.Redis(host=self.host, port=self.port)
        await self._redis.ping()
        logger.info("Успешное подключение к Redis")

    async def ping(self) -> bool:
        return bool(await self.client.ping())

    async def set(self, key: str, value: str, expire: int | None = None) -> None:
        await self.client.set(key, value, ex=expire)

    async def get(self, key: str) -> bytes | None:
        return await self.client.get(key)

    async def getdel(self, key: str) -> bytes | None:
        return await self.client.getdel(key)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def incr_with_expire(self, key: str, expire: int) -> int:
        """Атомарно увеличивает счётчик; TTL ставится при создании ключа."""
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, expire, nx=True)
            count, _ = await pipe.execute()
        return int(count)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
