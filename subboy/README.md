# Subboy — сайт для учёта подписок

Работает с **тем же бэкендом и БД**, что и Telegram-бот sub-tracker-bot.

## Как это устроено

1. **API** (FastAPI) в папке `web/` — те же таблицы и модели, что и у бота.
2. **Вход** — через [Telegram Login Widget](https://core.telegram.org/widgets/login): пользователь нажимает «Login with Telegram», Telegram отдаёт его id и hash, API проверяет hash и выдаёт JWT.
3. **Сайт** (`subboy/index.html`) — одна страница: список подписок и отчёт по расходам в месяц.

## Запуск у себя

### 1. Установить зависимости (раз уже стоят для бота — добавьте только для API)

```bash
pip install fastapi uvicorn pyjwt
```

Или из корня проекта:

```bash
pip install -r requirements.txt
```

### 2. Запустить API (и раздачу subboy)

Из корня проекта (где `bot.py`):

```bash
uvicorn web.main:app --host 0.0.0.0 --port 8000
```

- Сайт: **http://localhost:8000/** (откроется subboy).
- API: **http://localhost:8000/api/** (например `/api/health`, `/api/auth/telegram`, `/api/subscriptions`).

### 3. Включить кнопку «Login with Telegram»

В `subboy/index.html` задайте имя бота (без @):

```js
window.SUBBOY_BOT_USERNAME = 'ВашБотUsername';
```

Сайт должен открываться по **HTTPS** и с того домена, который указан в настройках бота в BotFather (или тот же домен для виджета). Для локальной проверки можно использовать «Войти по id» с hash от виджета, открытого на тестовом HTTPS.

### 4. Переменные окружения (.env)

Для API используются те же `BOT_TOKEN` и `DATABASE_URL`. По желанию можно добавить:

- `JWT_SECRET` — секрет для подписи JWT (если не задан, используется BOT_TOKEN).
- `WEB_ORIGIN` — разрешённый origin для CORS (по умолчанию `http://localhost:5173`).

## Деплой на сервер

- Запустите API рядом с ботом, например через systemd (отдельный юнит для `uvicorn web.main:app --host 0.0.0.0 --port 8000`).
- Настройте Nginx (или аналог) как reverse proxy на порт 8000, включите HTTPS.
- В `subboy/index.html` укажите `window.SUBBOY_BOT_USERNAME` и при необходимости домен для виджета.

После этого сайт subboy и бот используют одну БД и одних пользователей.
