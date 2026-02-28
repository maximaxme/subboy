# Деплой Subboy на Server 2 (85.239.40.133)

Выполняйте команды **на сервере** (Remote SSH в Cursor: `85.239.40.133`, папка `/opt/apps/subboy`).

---

## Шаг 1. Подключение и проверка Node/Python

В терминале Cursor (на сервере):

```bash
node -v
npm -v
python3 --version
```

**Если Node нет** — установить LTS:

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt-get update
apt-get install -y nodejs
node -v
npm -v
```

Если NodeSource недоступен (403), установить из репозитория Ubuntu:

```bash
apt-get update
apt-get install -y nodejs npm
```

**Python 3.10+** уже должен быть. Если нет:

```bash
apt-get install -y python3 python3-pip python3-venv
```

---

## Шаг 2. Команды запуска (уже определены)

| Компонент | Команда запуска |
|-----------|-----------------|
| **Бот**   | `python bot.py` (через venv: `/opt/apps/subboy/venv/bin/python bot.py`) |
| **Веб**   | `uvicorn web.main:app --host 0.0.0.0 --port 8000` (раздаёт API + статику из `subboy/dist`) |

Фронт (Vite/React) в `subboy/`: для прода собирается `npm run build` → `subboy/dist`, его раздаёт FastAPI.

---

## Шаг 3. Установка зависимостей

```bash
cd /opt/apps/subboy

# Python
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Фронт (для сборки dist)
cd subboy
npm ci || npm install
cd ..
```

---

## Шаг 4. Сборка фронта

```bash
cd /opt/apps/subboy/subboy
npm run build
cd /opt/apps/subboy
```

Проверка: должен появиться `subboy/dist/index.html`.

---

## Шаг 5. Env

```bash
# Создать .env из шаблона (если ещё нет)
cp -n /opt/apps/subboy/.env.example /etc/subboy/.env

# Если файла не было — отредактировать:
# nano /etc/subboy/.env
# Заполнить: BOT_TOKEN=..., DATABASE_URL=..., при необходимости JWT_SECRET, WEB_ORIGIN

chmod 600 /etc/subboy/.env
```

**Не коммитить секреты в git.** Все секреты только в `/etc/subboy/.env`.

---

## Шаг 6. Systemd

```bash
# Копировать unit-файлы из репозитория
cp /opt/apps/subboy/deploy/subboy.service     /etc/systemd/system/
cp /opt/apps/subboy/deploy/subboy-web.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable subboy subboy-web
systemctl start subboy subboy-web
systemctl status subboy --no-pager
systemctl status subboy-web --no-pager
```

Логи:

```bash
journalctl -u subboy     -n 100 --no-pager
journalctl -u subboy-web -n 100 --no-pager
# в реальном времени:
journalctl -u subboy     -f
journalctl -u subboy-web -f
```

---

## Итог

| Параметр | Значение |
|----------|----------|
| **Сервисы** | `subboy` (бот), `subboy-web` (API + сайт) |
| **Команда бота** | `venv/bin/python bot.py` |
| **Команда веб** | `venv/bin/uvicorn web.main:app --host 0.0.0.0 --port 8000` |
| **Порт** | 8000 (веб) |
| **Env** | `/etc/subboy/.env` |
| **Логи бота** | `journalctl -u subboy -f` |
| **Логи веб** | `journalctl -u subboy-web -f` |

Проверка: открыть в браузере `http://85.239.40.133:8000` и написать боту в Telegram.
