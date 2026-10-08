from fastapi import APIRouter, status
from fastapi_cache.decorator import cache

from src.api.dependencies import AdminDep, DBDep
from src.schemas.comforts import Comfort, ComfortAdd
from src.services.comforts import ComfortService
from src.utils.cache import COMFORTS_NAMESPACE

router = APIRouter(prefix="/comforts", tags=["Удобства"])


@router.get("", summary="Список удобств")
@cache(expire=60, namespace=COMFORTS_NAMESPACE)
async def get_all_comforts(db: DBDep) -> list[Comfort]:
    return await ComfortService(db).get_all_comforts()


@router.post("", summary="Создание удобства", status_code=status.HTTP_201_CREATED)
async def create_comfort(db: DBDep, _admin: AdminDep, comfort_data: ComfortAdd) -> Comfort:
    return await ComfortService(db).create_comfort(comfort_data)
