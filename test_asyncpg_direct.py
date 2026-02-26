"""
Прямой тест подключения через asyncpg
"""
import asyncio
import asyncpg

async def test_direct():
    try:
        print("Попытка прямого подключения через asyncpg...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='1245Gufumer',
            database='sub_tracker'
        )
        
        version = await conn.fetchval('SELECT version()')
        db_name = await conn.fetchval('SELECT current_database()')
        
        print(f"[OK] Подключение успешно!")
        print(f"База данных: {db_name}")
        print(f"Версия: {version.split(',')[0]}")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        print(f"Тип: {type(e).__name__}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_direct())
