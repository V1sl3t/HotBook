# HotBook

Сервис бронирования номеров в отелях (аналог «Островка»): поиск отелей и свободных
номеров на даты, бронирование, удобства номеров, загрузка фотографий.

Документация API: <https://hotbook.run.place/docs>

## Стек

- **Python 3.13**, **FastAPI**, Pydantic v2
- **SQLAlchemy 2** (async, asyncpg), **Alembic**, **PostgreSQL 16**
- **Redis**: кэш (fastapi-cache2), refresh-токены, rate limit, брокер Celery
- **Celery** + beat: ресайз картинок, письма о заезде
- Инструменты [Astral](https://astral.sh): **uv** (зависимости, `uv.lock`), **ruff** (линтер и форматтер), **ty** (типы)
- pytest, GitHub Actions, Docker, nginx, Prometheus-метрики, Sentry (опционально)

## API

Все эндпоинты под префиксом `/api/v1`, служебные — в корне.

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| POST | `/auth/register` | все | регистрация (пароль от 8 символов) → 201 |
| POST | `/auth/login` | все | вход: access и refresh в httpOnly-cookie, access также в теле |
| POST | `/auth/refresh` | refresh-cookie | новая пара токенов (refresh одноразовый) |
| GET | `/auth/me` | пользователь | текущий пользователь |
| POST | `/auth/logout` | все | выход, отзыв refresh-токена → 204 |
| GET | `/hotels?date_from&date_to&title&location&page&per_page` | все | отели со свободными номерами: `{items, total, page, per_page}` |
| GET | `/hotels/{id}` | все | отель (кэшируется) |
| POST/PUT/PATCH/DELETE | `/hotels[/{id}]` | админ | управление отелями |
| GET | `/hotels/{id}/rooms?date_from&date_to` | все | свободные номера отеля |
| GET | `/hotels/{id}/rooms/{room_id}` | все | номер с удобствами |
| POST/PUT/PATCH/DELETE | `/hotels/{id}/rooms[/{room_id}]` | админ | управление номерами |
| GET | `/comforts` | все | удобства (кэшируется) |
| POST | `/comforts` | админ | новое удобство |
| POST | `/bookings` | пользователь | бронь → 201 |
| GET | `/bookings/me` | пользователь | мои брони |
| GET | `/bookings` | админ | все брони |
| POST | `/images` | админ | загрузка JPEG/PNG/WEBP до 5 МБ, раздаётся из `/media/images/` |
| GET | `/health`, `/ready` | все | liveness / readiness (БД и Redis) |
| GET | `/metrics` | только внутри сети | метрики Prometheus (nginx закрывает снаружи) |

Авторизация: httpOnly-cookie `access_token` или заголовок `Authorization: Bearer <token>`
(кнопка **Authorize** в Swagger). Ошибки всегда в формате `{"detail": ...}`.

## Запуск в Docker

```sh
cp .env.example .env   # заполнить пароли и JWT_SECRET_KEY
docker compose up -d --build
docker compose exec api python -m src.cli make-admin you@example.com
```

Compose поднимает Postgres, Redis, одноразовый сервис миграций, API, Celery worker и beat, nginx.
Сертификаты Let's Encrypt монтируются из `/etc/letsencrypt`, webroot для продления —
`/var/www/certbot`.

**Переход с прежней схемы запуска** (`docker run` для БД, Redis и nginx): остановите старые
контейнеры (`docker rm -f booking_db booking_cache booking_nginx booking_back
booking_celery_worker booking_celery_beat`) и выполните `docker compose up -d --build`.
Том `pg-booking-data` подключится как есть, миграции применятся автоматически.
После обновления API доступно под `/api/v1`, а создавать отели, номера и удобства может
только администратор, поэтому назначьте его командой выше.

## Локальная разработка

```sh
uv sync                              # окружение и зависимости из uv.lock
docker compose up -d db redis        # или свои Postgres и Redis
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
uv run --with pre-commit pre-commit install   # ruff и uv-lock перед коммитом
```

Проверки (то же самое запускает CI):

```sh
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest --cov
```

Тесты берут настройки из `.env-test` и ожидают Postgres на `localhost:5432`
(пользователь `postgres`, пароль `1234`, база `test`) и Redis на `localhost:6379`.
Таблицы в базе `test` пересоздаются при каждом запуске.

## Автор

V1sl3t
