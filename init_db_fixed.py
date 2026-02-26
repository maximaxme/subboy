"""
Скрипт для создания таблиц в базе данных (улучшенная версия)
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from database.models import Base
from config import config

async def init_db():
    """Создает все таблицы в базе данных"""
    try:
        print("Подключение к базе данных...")
        
        # Создаем engine с дополнительными параметрами
        engine = create_async_engine(
            config.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,  # Проверка соединения перед использованием
            pool_recycle=3600,   # Переподключение каждые 3600 секунд
        )
        
        print("Создание таблиц...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("[OK] Таблицы успешно созданы!")
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        print("\nВозможные причины:")
        print("  1. База данных sub_tracker не создана")
        print("  2. Неправильный пароль в .env файле")
        print("  3. PostgreSQL не запущен")
        print("  4. Проблема с подключением")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(init_db())
        if result:
            print("\n[SUCCESS] Vse gotovo! Mozhno zapuskat' bota: python bot.py")
        else:
            print("\n[ERROR] Nuzhno ispravit' problemy")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        sys.exit(1)
