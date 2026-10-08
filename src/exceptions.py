from datetime import date


class HotBookException(Exception):
    """Базовое доменное исключение.

    Глобальный обработчик в ``src.main`` превращает его в HTTP-ответ
    с ``status_code`` и ``detail`` текущего класса.
    """

    status_code: int = 500
    detail: str = "Неожиданная ошибка"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class ObjectNotFoundException(HotBookException):
    status_code = 404
    detail = "Объект не найден"


class UserNotFoundException(ObjectNotFoundException):
    detail = "Пользователь не найден"


class HotelNotFoundException(ObjectNotFoundException):
    detail = "Отель не найден"


class RoomNotFoundException(ObjectNotFoundException):
    detail = "Номер не найден"


class ComfortNotFoundException(ObjectNotFoundException):
    detail = "Удобство не найдено"


class ObjectAlreadyExistsException(HotBookException):
    status_code = 409
    detail = "Похожий объект уже существует"


class UserAlreadyExistsException(ObjectAlreadyExistsException):
    detail = "Пользователь с такой почтой уже существует"


class ObjectInUseException(HotBookException):
    status_code = 409
    detail = "Объект используется другими данными и не может быть изменён или удалён"


class AllRoomsAreBookedException(HotBookException):
    status_code = 409
    detail = "Все номера забронированы"


class InvalidDateRangeException(HotBookException):
    status_code = 422
    detail = "Дата выезда должна быть позже даты заезда"


class InvalidImageException(HotBookException):
    status_code = 422
    detail = "Файл не является изображением JPEG, PNG или WEBP"


class FileTooLargeException(HotBookException):
    status_code = 413
    detail = "Файл слишком большой"


class AuthException(HotBookException):
    status_code = 401
    detail = "Требуется авторизация"


class InvalidCredentialsException(AuthException):
    detail = "Неверный email или пароль"


class IncorrectTokenException(AuthException):
    detail = "Невалидный токен"


class NoAccessTokenException(AuthException):
    detail = "Не предоставлен access токен"


class PermissionDeniedException(HotBookException):
    status_code = 403
    detail = "Недостаточно прав"


class TooManyRequestsException(HotBookException):
    status_code = 429
    detail = "Слишком много попыток, попробуйте позже"


def check_date_to_after_date_from(date_from: date, date_to: date) -> None:
    if date_to <= date_from:
        raise InvalidDateRangeException
