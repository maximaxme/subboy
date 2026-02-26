# Настройка базы данных PostgreSQL

## Если PostgreSQL уже установлен:

1. **Узнайте параметры подключения:**
   - **Username (имя пользователя)**: обычно `postgres` (по умолчанию)
   - **Password (пароль)**: тот, который вы указали при установке PostgreSQL
   - **Host**: `localhost` (если база на вашем компьютере)
   - **Port**: `5432` (стандартный порт)
   - **Database**: создайте новую базу данных (например, `sub_tracker`)

2. **Создайте базу данных:**
   
   Через командную строку:
   ```bash
   psql -U postgres
   CREATE DATABASE sub_tracker;
   \q
   ```
   
   Или через pgAdmin (графический интерфейс)

3. **Обновите файл `.env`:**
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:ваш_пароль@localhost:5432/sub_tracker
   ```
   
   Замените `ваш_пароль` на реальный пароль от PostgreSQL

## Примеры DATABASE_URL:

**Стандартная установка:**
```
DATABASE_URL=postgresql+asyncpg://postgres:mypassword@localhost:5432/sub_tracker
```

**Если другой пользователь:**
```
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/sub_tracker
```

**Если PostgreSQL на другом компьютере:**
```
DATABASE_URL=postgresql+asyncpg://username:password@192.168.1.100:5432/sub_tracker
```

## Если PostgreSQL НЕ установлен:

### Установка PostgreSQL:

1. Скачайте установщик: https://www.postgresql.org/download/windows/
2. Запустите установщик и следуйте инструкциям
3. **Важно**: Запомните пароль для пользователя `postgres`!
4. После установки создайте базу данных (см. выше)

### Альтернатива: Использовать SQLite (проще, но требует изменения кода)

Если не хотите устанавливать PostgreSQL, можно использовать SQLite, но нужно:
1. Изменить код для работы с SQLite
2. Установить `aiosqlite` вместо `asyncpg`

---

## Проверка подключения:

После настройки `.env`, попробуйте запустить:
```bash
python init_db.py
```

Если всё правильно, вы увидите: "✅ Таблицы успешно созданы!"
