# Production Control

## Описание

Сервис для управления производственными батчами, агрегации данных и настройки вебхуков для внешних систем.

## Стек

* Core: Python 3.13, FastAPI.

* Database: PostgreSQL, SQLAlchemy (ORM), Alembic (миграции).

* Task Queue: Celery, RabbitMQ (брокер сообщений), Redis (кэширование).

* Storage & Files: MinIO (S3), OpenPyXL (Excel), WeasyPrint (PDF).

* Dev Tools: Ruff, Black, Pytest, MyPy, Pre-commit.

## Запуск проекта

Для локального запуска убедитесь, что у вас установлен Docker и Docker Compose.

`docker compose up -d`

## Запуск тестов

Для проверки работоспособности системы используйте bash-скрипт. Он автоматически подготовит базу данных и запустит
pytest:

**Дайте права на исполнение (один раз)**

`chmod +x run_tests.sh`

**Запуск тестов**

`./run_tests.sh`
