"""
Скрипт для проверки базы данных и таблиц
"""
import asyncio
import sys
from database.db_helper import db_helper
from database.models import Base
from sqlalchemy import inspect, text

async def check_database():
    """Проверяет наличие базы данных и таблиц"""
    try:
        print("Проверка подключения к базе данных...")
        
        # Проверяем подключение
        async with db_helper.engine.begin() as conn:
            result = await conn.execute(text("SELECT current_database();"))
            db_name = result.scalar()
            print(f"[OK] Подключение успешно! База данных: {db_name}")
            
            # Проверяем наличие таблиц
            print("\nПроверка таблиц...")
            inspector = inspect(db_helper.engine.sync_engine)
            tables = inspector.get_table_names()
            
            if tables:
                print(f"[OK] Найдено таблиц: {len(tables)}")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("[WARNING] Таблицы не найдены!")
                print("   Запустите: python init_db.py")
                return False
            
            # Проверяем наличие нужных таблиц
            required_tables = ['users', 'categories', 'subscriptions', 'notification_settings']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print(f"\n[WARNING] Отсутствуют таблицы: {', '.join(missing_tables)}")
                print("   Запустите: python init_db.py")
                return False
            else:
                print("\n[OK] Все необходимые таблицы созданы!")
                return True
                
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        print("\nВозможные причины:")
        print("  1. База данных sub_tracker не создана")
        print("  2. Неправильный пароль в .env файле")
        print("  3. PostgreSQL не запущен")
        return False
    finally:
        await db_helper.dispose()

if __name__ == "__main__":
    result = asyncio.run(check_database())
    if result:
        print("\n[SUCCESS] Vse gotovo! Mozhno zapuskat' bota: python bot.py")
    else:
        print("\n[ERROR] Nuzhno ispravit' problemy pered zapuskom bota")
