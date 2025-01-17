# HotBook

## Описание
Проект "HotBook" – это сервис, который позволяет бронировать номера отелей и добавлять удобства в выбранный номер. Аналог "Ostrovok.ru"


## Стек проекта
- Python 
- FastAPI
- Pydantic 
- SQLalchemy
- Alembic
- PosgreSQL
- Redis
- Celery
- pytest
- ruff
- Nginx
- Docker

## Ссылка на развернутый проект
(https://hotbook.run.place/docs)

## Процесс запуска проекта 

```sh
docker run --name booking_db \
    -p 6432:5432 \
    -e POSTGRES_USER=abcde \
    -e POSTGRES_PASSWORD=abcde \
    -e POSTGRES_DB=booking \
    --network=myNetwork \
    --volume pg-booking-data:/var/lib/postgresql/data \
    -d postgres:16

docker run --name booking_cache \
    -p 7379:6379 \
    --network=myNetwork \
    -d redis:7.4

docker run --name booking_nginx \
    --volume ./nginx.conf:/etc/nginx/nginx.conf \
    --volume /etc/letsencrypt:/etc/letsencrypt \
    --volume /var/lib/letsencrypt:/var/lib/letsencrypt \
    --network=myNetwork \
    --rm -p 80:80 -p 443:443 -d nginx

docker compose up -d 
```

## Автор проекта 
 
V1sl3t
