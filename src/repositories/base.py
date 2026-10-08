import logging
from collections.abc import Sequence
from typing import Any, ClassVar

from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError
from pydantic import BaseModel
from sqlalchemy import CursorResult, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from src.exceptions import (
    ObjectAlreadyExistsException,
    ObjectInUseException,
    ObjectNotFoundException,
)
from src.repositories.mappers.base import DataMapper

logger = logging.getLogger(__name__)


class BaseRepository:
    model: ClassVar[type[Any]]
    mapper: ClassVar[type[DataMapper]]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _execute_write(self, stmt: Executable) -> CursorResult[Any]:
        """Выполняет изменяющий запрос и переводит ошибки целостности в доменные."""
        try:
            return await self.session.execute(stmt)  # ty: ignore[invalid-return-type]
        except IntegrityError as ex:
            cause = ex.orig.__cause__ if ex.orig is not None else None
            if isinstance(cause, UniqueViolationError):
                raise ObjectAlreadyExistsException from ex
            if isinstance(cause, ForeignKeyViolationError):
                raise ObjectInUseException from ex
            logger.exception("Незнакомая ошибка целостности при записи в %s", self.model.__name__)
            raise

    async def get_filtered(self, *filter: Any, **filter_by: Any) -> list[Any]:
        query = select(self.model).filter(*filter).filter_by(**filter_by).order_by(self.model.id)
        result = await self.session.execute(query)
        return [self.mapper.map_to_domain_entity(model) for model in result.scalars().all()]

    async def get_all(self) -> list[Any]:
        return await self.get_filtered()

    async def count(self, *filter: Any, **filter_by: Any) -> int:
        query = select(func.count()).select_from(self.model).filter(*filter).filter_by(**filter_by)
        return (await self.session.execute(query)).scalar_one()

    async def get_one_or_none(self, **filter_by: Any) -> Any | None:
        query = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(query)
        model = result.scalars().one_or_none()
        if model is None:
            return None
        return self.mapper.map_to_domain_entity(model)

    async def get_one(self, **filter_by: Any) -> Any:
        model = await self.get_one_or_none(**filter_by)
        if model is None:
            raise ObjectNotFoundException
        return model

    async def add(self, data: BaseModel) -> Any:
        add_stmt = insert(self.model).values(**data.model_dump()).returning(self.model)
        result = await self._execute_write(add_stmt)
        return self.mapper.map_to_domain_entity(result.scalars().one())

    async def add_bulk(self, data: Sequence[BaseModel]) -> None:
        if not data:
            return
        add_stmt = insert(self.model).values([item.model_dump() for item in data])
        await self._execute_write(add_stmt)

    async def edit(self, data: BaseModel, exclude_unset: bool = False, **filter_by: Any) -> int:
        """Обновляет строки и возвращает их количество (0 — ничего не найдено)."""
        values = data.model_dump(exclude_unset=exclude_unset)
        if not values:
            return await self.count(**filter_by)
        edit_stmt = update(self.model).filter_by(**filter_by).values(**values)
        result = await self._execute_write(edit_stmt)
        return result.rowcount

    async def delete(self, **filter_by: Any) -> int:
        """Удаляет строки и возвращает их количество (0 — ничего не найдено)."""
        delete_stmt = delete(self.model).filter_by(**filter_by)
        result = await self._execute_write(delete_stmt)
        return result.rowcount
