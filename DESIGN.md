# Проектирование: Telegram-бот для трекинга подписок

## 🧩 Этап 0: Проектирование

### Архитектура
Для обеспечения поддерживаемости и масштабируемости будем использовать многослойную архитектуру.

- **`bot.py`**: Точка входа, инициализация бота и диспетчера.
- **`config.py`**: Управление конфигурацией через `pydantic-settings`.
- **`handlers/`**: Обработчики событий Telegram.
  - `start.py`: Команда /start и главное меню.
  - `subscriptions.py`: Управление подписками (CRUD).
  - `categories.py`: Управление категориями.
  - `reports.py`: Отчеты по расходам.
  - `settings.py`: Настройки уведомлений.
- **`services/`**: Бизнес-логика.
  - `subscription_service.py`: Расчет ежемесячной стоимости из годовых подписок.
  - `report_service.py`: Агрегация данных для отчетов.
- **`database/`**: Взаимодействие с базой данных.
  - `models.py`: Модели SQLAlchemy.
  - `db_helper.py`: Управление подключениями и паттерны репозиториев.
- **`utils/`**: Общие утилиты.
- **`middlewares/`**: Регистрация пользователей и ограничение частоты запросов (rate-limiting).

### Состояния FSM (aiogram 3.x)

- `AddingSubscription` (Добавление подписки):
  - `name`: Ожидание названия подписки.
  - `price`: Ожидание суммы.
  - `period`: Выбор периода (месяц/год).
  - `category`: Выбор категории.
  - `date`: Выбор даты следующего списания.

- `ManagingCategories` (Управление категориями):
  - `name`: Ввод названия новой или переименованной категории.

### Схема БД (PostgreSQL)

```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY, -- Telegram User ID
    username TEXT,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    UNIQUE(user_id, name)
);

CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    period TEXT NOT NULL, -- 'monthly', 'yearly'
    next_payment DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notification_settings (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    day_before BOOLEAN DEFAULT TRUE,
    weekly BOOLEAN DEFAULT TRUE,
    monthly BOOLEAN DEFAULT FALSE
);
```

### UX/UI Стратегия
- Максимальное использование Inline-кнопок.
- Минимальный ввод текста (только для имен и сумм).
- Понятные сообщения с использованием эмодзи.
