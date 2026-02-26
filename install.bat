@echo off
echo Установка зависимостей для бота...
python -m pip install aiogram sqlalchemy[asyncio] asyncpg pydantic-settings python-dotenv alembic
pause
