from collections.abc import Iterable

from src.exceptions import ComfortNotFoundException
from src.schemas.comforts import Comfort, ComfortAdd
from src.services.base import BaseService
from src.utils.cache import COMFORTS_NAMESPACE, invalidate


class ComfortService(BaseService):
    async def create_comfort(self, data: ComfortAdd) -> Comfort:
        comfort = await self.db.comforts.add(data)
        await self.db.commit()
        await invalidate(COMFORTS_NAMESPACE)
        return comfort

    async def get_all_comforts(self) -> list[Comfort]:
        return await self.db.comforts.get_all()

    async def check_comforts_exist(self, comforts_ids: Iterable[int]) -> None:
        wanted = set(comforts_ids)
        if wanted - await self.db.comforts.get_existing_ids(wanted):
            raise ComfortNotFoundException
