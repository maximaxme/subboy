# Бот на Timeweb перестал работать — диагностика

Если бот, развёрнутый на Timeweb, перестал отвечать в Telegram, пройдите по шагам ниже.

---

## 1. Подключитесь к серверу

```bash
ssh root@ВАШ_IP_АДРЕС
```

---

## 2. Проверьте, запущена ли служба бота

```bash
sudo systemctl status sub-tracker-bot
```

- **`active (running)`** — служба работает. Тогда смотрите раздел «Логи» ниже.
- **`inactive (dead)`** или **`failed`** — служба не запущена или упала. Запустите и смотрите логи:

```bash
sudo systemctl start sub-tracker-bot
sudo journalctl -u sub-tracker-bot -n 100 --no-pager
```

---

## 3. Посмотрите логи бота

```bash
sudo journalctl -u sub-tracker-bot -n 200 --no-pager
```

Или в реальном времени:

```bash
sudo journalctl -u sub-tracker-bot -f
```

Типичные причины по логам:

| Сообщение в логах | Что делать |
|-------------------|------------|
| `Unauthorized` / `401` | Токен бота неверный или отозван. Получите новый у @BotFather и обновите `BOT_TOKEN` в `.env`, затем `sudo systemctl restart sub-tracker-bot`. |
| `connection refused` / `ConnectionRefusedError` к `localhost:5432` | PostgreSQL не запущен. Запустите: `sudo systemctl start postgresql`. |
| `password authentication failed` / `asyncpg.exceptions.InvalidPasswordError` | Неверный пароль в `DATABASE_URL`. Проверьте `.env` и пароль пользователя БД. |
| `ConnectionDoesNotExistError` / `connection was closed` | Проблема с БД (разрыв соединения). Перезапустите PostgreSQL и бота: `sudo systemctl restart postgresql && sudo systemctl restart sub-tracker-bot`. |
| `ModuleNotFoundError` / `ImportError` | Зависимости не установлены или другой Python. Зайдите в проект, активируйте venv и переустановите: `cd /opt/sub-tracker-bot && source venv/bin/activate && pip install -r requirements.txt`, затем перезапустите бота. |
| Нет логов / пусто | Служба могла упасть до вывода. Запустите бота вручную (см. п. 5) и смотрите вывод в терминале. |

---

## 4. Проверьте PostgreSQL

```bash
sudo systemctl status postgresql
```

Должно быть **`active (running)`**. Если нет:

```bash
sudo systemctl start postgresql
```

Проверка входа в БД (подставьте пользователя и имя БД из вашего `.env`):

```bash
sudo -u postgres psql -c "\l"
```

---

## 5. Запуск бота вручную (чтобы увидеть ошибку в консоли)

```bash
cd /opt/sub-tracker-bot
source venv/bin/activate
python bot.py
```

Смотрите вывод в терминале. Часто здесь сразу видно:
- неверный `BOT_TOKEN`;
- ошибка подключения к БД (хост, порт, пароль);
- отсутствующий модуль.

Остановка: **Ctrl+C**.

---

## 6. Проверьте файл .env

```bash
cd /opt/sub-tracker-bot
cat .env
```

Убедитесь, что:
- `BOT_TOKEN` — актуальный токен от @BotFather (без лишних пробелов и кавычек);
- `DATABASE_URL` — правильный хост (например `localhost`), порт `5432`, логин, пароль и имя БД.

После изменения `.env`:

```bash
sudo systemctl restart sub-tracker-bot
```

---

## 7. Место на диске и память

Иногда сервер перестаёт нормально работать из-за нехватки места или RAM.

```bash
df -h
free -h
```

Если диск заполнен — удалите старые логи или временные файлы. Если памяти мало — перезапустите бота и при необходимости перезагрузите сервер.

---

## 8. Перезапуск бота и API (если используете сайт)

```bash
sudo systemctl restart sub-tracker-bot
# Если у вас запущен и сайт Subboy:
sudo systemctl restart sub-tracker-api
```

Проверка статуса:

```bash
sudo systemctl status sub-tracker-bot
sudo systemctl status sub-tracker-api
```

---

## Краткий чеклист

1. `systemctl status sub-tracker-bot` — служба в состоянии **active (running)**?
2. `journalctl -u sub-tracker-bot -n 100` — есть ли ошибки в логах?
3. `systemctl status postgresql` — PostgreSQL запущен?
4. В `.env` верные `BOT_TOKEN` и `DATABASE_URL`?
5. Запуск `python bot.py` вручную из `/opt/sub-tracker-bot` с активированным venv — какая ошибка в консоли?

После исправления причины не забудьте: `sudo systemctl restart sub-tracker-bot`.
