"""
Скрипт для создания таблиц в базе данных
Запустите этот файл один раз перед первым запуском бота
"""
import asyncio
from database.db_helper import db_helper
from database.models import Base

async def init_db():
    """Создает все таблицы в базе данных"""
    async with db_helper.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблицы успешно созданы!")
    await db_helper.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
