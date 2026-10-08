from src.utils.db_manager import DBManager


class BaseService:
    def __init__(self, db: DBManager | None = None) -> None:
        self._db = db

    @property
    def db(self) -> DBManager:
        if self._db is None:
            raise RuntimeError(f"{type(self).__name__} создан без DBManager")
        return self._db
