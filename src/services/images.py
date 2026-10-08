import uuid
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

from src.config import settings
from src.exceptions import FileTooLargeException, InvalidImageException

# Формат определяется по содержимому файла, а не по имени или Content-Type от клиента.
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def images_dir() -> Path:
    path = settings.MEDIA_DIR / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path


class ImagesService:
    def save_image(self, file: BinaryIO) -> str:
        """Проверяет и сохраняет картинку под случайным именем, возвращает имя файла."""
        data = file.read(settings.MAX_UPLOAD_BYTES + 1)
        if len(data) > settings.MAX_UPLOAD_BYTES:
            raise FileTooLargeException
        try:
            with Image.open(BytesIO(data)) as img:
                image_format = img.format
                img.verify()
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as ex:
            raise InvalidImageException from ex
        if image_format not in ALLOWED_FORMATS:
            raise InvalidImageException

        # Имя клиента не используется вовсе: это исключает path traversal и перезапись файлов.
        filename = f"{uuid.uuid4().hex}{ALLOWED_FORMATS[image_format]}"
        (images_dir() / filename).write_bytes(data)
        return filename
