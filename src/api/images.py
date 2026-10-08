from fastapi import APIRouter, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from src.api.dependencies import AdminDep
from src.services.images import ImagesService
from src.tasks.tasks import resize_image

router = APIRouter(prefix="/images", tags=["Изображения отелей"])


class ImageUploaded(BaseModel):
    filename: str
    url: str


@router.post("", summary="Загрузка изображения", status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile, _admin: AdminDep) -> ImageUploaded:
    filename = await run_in_threadpool(ImagesService().save_image, file.file)
    await run_in_threadpool(resize_image.delay, filename)
    return ImageUploaded(filename=filename, url=f"/media/images/{filename}")
