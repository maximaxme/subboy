-- SQL скрипт для создания таблиц вручную через pgAdmin
-- Выполните этот скрипт в pgAdmin: Tools -> Query Tool -> вставьте код -> Execute

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    username VARCHAR,
    full_name VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица категорий
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Таблица подписок
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    category_id INTEGER,
    name VARCHAR NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    period VARCHAR NOT NULL,
    next_payment DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- Таблица настроек уведомлений
CREATE TABLE IF NOT EXISTS notification_settings (
    user_id BIGINT PRIMARY KEY,
    day_before BOOLEAN DEFAULT TRUE,
    weekly BOOLEAN DEFAULT TRUE,
    monthly BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
