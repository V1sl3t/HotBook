# CLAUDE.md

HotBook — API бронирования отелей на FastAPI + async SQLAlchemy + PostgreSQL + Redis + Celery.
Python 3.13, инструменты Astral: uv, ruff, ty.

## Команды

```sh
uv sync                                   # зависимости (только через uv add / uv remove)
uv run ruff check --fix . && uv run ruff format .
uv run ty check
uv run pytest                             # нужны Postgres и Redis, см. ниже
uv run pytest --cov
uv run alembic revision --autogenerate -m "..."   # затем проверить и поправить файл руками
uv run alembic upgrade head
uv run alembic check                      # модели и миграции должны совпадать (это есть в CI)
uv run python -m src.cli make-admin user@example.com [--revoke]
docker compose up -d --build              # весь стек
```

Тестам нужны Postgres `localhost:5432` (postgres/1234, база `test`) и Redis `localhost:6379`;
настройки берутся из `.env-test` (`MODE=TEST`, иначе conftest падает). Для alembic вне
docker: `set -a && . ./.env-test && set +a`.

## Архитектура

`src/api` (роутеры) → `src/services` (бизнес-логика, транзакции) → `src/repositories`
(запросы, `mappers` ORM → Pydantic) → `src/models` (ORM). Схемы в `src/schemas`.

- `DBManager` (`src/utils/db_manager.py`) — unit of work: одна сессия на запрос, все
  репозитории как атрибуты; без `commit()` изменения откатываются в `__aexit__`.
- Зависимости FastAPI в `src/api/dependencies.py`: `DBDep`, `UserIdDep`, `CurrentUserDep`,
  `AdminDep`, `PaginationDep`.
- Все роутеры подключаются под `/api/v1` в `src/main.py`; `/health`, `/ready`, `/metrics`,
  `/media` — в корне.
- Celery: `src/tasks` (`task_always_eager` при `MODE=TEST`), письма через `src/utils/email.py`.

## Соглашения

- **Ошибки:** только доменные исключения из `src/exceptions.py` со своим `status_code`;
  глобальный обработчик в `src/main.py` превращает их в `{"detail": ...}`. Не бросать
  `HTTPException` и не писать try/except-маппинг в роутерах.
- **Транзакции:** `commit()` вызывают только сервисы. `BaseRepository.edit/delete` возвращают
  число строк: 0 означает «не найдено» → сервис бросает `*NotFoundException`.
  `IntegrityError` переводится в 409 (`ObjectAlreadyExists` / `ObjectInUse`) в `_execute_write`.
- **Доступ:** любая запись, кроме броней, — только через `AdminDep`; брони — `UserIdDep`.
  Новый эндпоинт без зависимости доступа должен быть публичным осознанно.
- **Брони:** период полуоткрытый `[date_from, date_to)`; доступность считает
  `repositories/utils.rooms_ids_for_booking`; `add_booking` блокирует строку номера
  (`FOR UPDATE`) — не убирать, иначе овербукинг (`tests/.../bookings/test_db.py`).
- **Ответы:** у эндпоинтов возвращаемый тип = `response_model`; POST → 201 с объектом,
  PUT/PATCH → объект, DELETE → 204.
- **Кэш:** только `@cache(namespace=...)` с ключом из `src/utils/cache.py`
  (по пути и query, не по аргументам функции). После записи — `invalidate(namespace)`.
  Не кэшировать доступность и личные данные.
- **Модели:** любое изменение — миграция в `src/migrations/versions` + `alembic check`.
  Новые CHECK на заполненные таблицы — через `NOT VALID`.
- **Загрузки:** имя файла клиента не используется; проверка формата Pillow, лимит размера.
- **Тесты:** к каждому багфиксу — тест. Фикстуры `ac` (аноним), `user_ac`, `admin_ac`,
  `db`; даты брони через `future(days)`. Email в тестах — `@example.com` (домены `.test`
  отклоняет email-validator). Тест должен проходить и при запуске отдельного файла.
- Стиль: ruff (line-length 100), строки и сообщения для пользователя — на русском.
