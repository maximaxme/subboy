"""
Тестовый скрипт для проверки подключения к базе данных
"""
import asyncio
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import config

async def test_connection():
    """Тестирует подключение к базе данных"""
    try:
        # Парсим URL и кодируем пароль
        db_url = config.DATABASE_URL
        
        # Если пароль содержит специальные символы, нужно его закодировать
        # Разбиваем URL на части
        if "://" in db_url:
            parts = db_url.split("://")
            scheme = parts[0]
            rest = parts[1]
            
            # Ищем пароль в URL
            if "@" in rest:
                user_pass, host_db = rest.split("@", 1)
                if ":" in user_pass:
                    user, password = user_pass.split(":", 1)
                    # Кодируем пароль
                    encoded_password = quote_plus(password)
                    # Собираем URL обратно
                    db_url = f"{scheme}://{user}:{encoded_password}@{host_db}"
        
        print(f"Попытка подключения...")
        print(f"URL: {db_url.replace(config.DATABASE_URL.split('@')[0].split(':')[-1], '***')}")
        
        engine = create_async_engine(
            db_url,
            pool_pre_ping=True,
            echo=False
        )
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT current_database(), version();"))
            row = result.fetchone()
            print(f"[OK] Подключение успешно!")
            print(f"База данных: {row[0]}")
            print(f"Версия PostgreSQL: {row[1].split(',')[0]}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка подключения: {e}")
        print(f"\nТип ошибки: {type(e).__name__}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    if not result:
        print("\nВозможные решения:")
        print("1. Проверьте, что PostgreSQL запущен")
        print("2. Проверьте пароль в .env файле")
        print("3. Проверьте, что база данных sub_tracker существует")
        print("4. Попробуйте перезапустить PostgreSQL")
