# 🚀 Быстрый старт

## После установки PostgreSQL:

### 1. Создайте базу данных

**Вариант А - через командную строку:**
```bash
psql -U postgres
```
Введите пароль, затем:
```sql
CREATE DATABASE sub_tracker;
\q
```

**Вариант Б - через pgAdmin:**
1. Откройте pgAdmin (должен быть в меню Пуск)
2. Подключитесь к серверу (пароль от postgres)
3. Правой кнопкой на "Databases" → "Create" → "Database"
4. Имя: `sub_tracker` → OK

### 2. Настройте .env файл

Откройте файл `.env` и замените:
```
DATABASE_URL=postgresql+asyncpg://postgres:ВАШ_ПАРОЛЬ@localhost:5432/sub_tracker
```

**Пример:**
Если пароль `mypass123`, то:
```
DATABASE_URL=postgresql+asyncpg://postgres:mypass123@localhost:5432/sub_tracker
```

### 3. Установите зависимости Python

```bash
python -m pip install aiogram sqlalchemy[asyncio] asyncpg pydantic-settings python-dotenv alembic
```

### 4. Создайте таблицы

```bash
python init_db.py
```

Должно появиться: "✅ Таблицы успешно созданы!"

### 5. Запустите бота

```bash
python bot.py
```

Готово! 🎉
