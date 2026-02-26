# Развёртывание бота на Timeweb Cloud

Пошаговая инструкция, как запустить **sub-tracker-bot** на сервере Timeweb, чтобы он работал онлайн 24/7.

---

## 1. Что нужно на Timeweb

- **Облачный сервер (VPS)** в [Timeweb Cloud](https://timeweb.cloud/services/cloud-servers)
  - Подойдёт тариф от **Cloud MSK 15** (1 ГБ RAM, 15 ГБ NVMe)
  - ОС: **Ubuntu 22.04** (рекомендуется)

- **PostgreSQL** — можно установить на тот же сервер (инструкция ниже) или использовать управляемую БД Timeweb, если она есть в вашем тарифе.

---

## 2. Создание сервера в Timeweb

1. Зайдите в [timeweb.cloud](https://timeweb.cloud) → **Облачные серверы** → **Создать сервер**.
2. Выберите:
   - Регион (например, Москва).
   - ОС: **Ubuntu 22.04**.
   - Тариф: минимум 1 ГБ RAM.
3. Сохраните **IP-адрес**, **логин** (часто `root`) и **пароль** (или ключ SSH).

---

## 3. Подключение к серверу

С Windows можно использовать:

- **PowerShell** + SSH: `ssh root@ВАШ_IP`
- Или **PuTTY** / **Windows Terminal**.

```bash
ssh root@ВАШ_IP_АДРЕС
```

Введите пароль при запросе.

---

## 4. Подготовка сервера (Ubuntu)

Выполните команды по очереди:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Python 3.10+ и venv
sudo apt install -y python3 python3-pip python3-venv

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Git (чтобы клонировать проект или загружать обновления)
sudo apt install -y git
```

---

## 5. Настройка PostgreSQL

```bash
# Переключиться на пользователя postgres
sudo -u postgres psql

# В консоли PostgreSQL выполнить:
CREATE USER botuser WITH PASSWORD 'ваш_надёжный_пароль';
CREATE DATABASE subtracker OWNER botuser;
\q
```

Пароль замените на свой. Для доступа с localhost прав обычно достаточно.

Проверка:

```bash
sudo -u postgres psql -c "\l"
```

Должна быть БД `subtracker`.

---

## 6. Загрузка проекта на сервер

### Вариант А: через Git (если проект в GitHub/GitLab)

На сервере:

```bash
cd /opt
sudo git clone https://github.com/ВАШ_ЛОГИН/sub-tracker-bot.git
sudo chown -R $USER:$USER sub-tracker-bot
cd sub-tracker-bot
```

### Вариант Б: через SCP/SFTP с вашего ПК

На **вашем компьютере** (в PowerShell, в папке с проектом):

```powershell
scp -r C:\Users\evil-\sub-tracker-bot root@ВАШ_IP:/opt/sub-tracker-bot
```

На сервере:

```bash
cd /opt/sub-tracker-bot
```

### Вариант В: архив по SCP

На ПК создайте архив (без `.env` и `__pycache__`), затем:

```powershell
scp sub-tracker-bot.zip root@ВАШ_IP:/opt/
```

На сервере:

```bash
cd /opt && unzip sub-tracker-bot.zip && mv sub-tracker-bot-master sub-tracker-bot  # или как распаковалось
cd sub-tracker-bot
```

---

## 7. Виртуальное окружение и зависимости

На сервере в каталоге проекта:

```bash
cd /opt/sub-tracker-bot

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

---

## 8. Переменные окружения (.env)

Создайте файл `.env` на сервере:

```bash
nano .env
```

Содержимое (подставьте свои значения):

```env
BOT_TOKEN=123456789:ABCdefGHI...
DATABASE_URL=postgresql+asyncpg://botuser:ваш_надёжный_пароль@localhost:5432/subtracker
```

- `BOT_TOKEN` — токен от @BotFather.
- `DATABASE_URL` — пользователь, пароль и имя БД из шага 5.

Сохраните: `Ctrl+O`, Enter, `Ctrl+X`.

---

## 9. Создание таблиц в БД

Если в проекте есть скрипты миграций или создания таблиц:

```bash
# В каталоге проекта, с активированным venv
source /opt/sub-tracker-bot/venv/bin/activate
cd /opt/sub-tracker-bot

# Если есть Alembic
alembic upgrade head

# Или выполните create_tables.sql (подставьте пароль от botuser):
PGPASSWORD='ваш_надёжный_пароль' psql -U botuser -d subtracker -h localhost -f create_tables.sql
```

---

## 10. Проверка запуска вручную

```bash
source /opt/sub-tracker-bot/venv/bin/activate
cd /opt/sub-tracker-bot
python bot.py
```

В Telegram напишите боту. Если всё отвечает — останавливайте: `Ctrl+C`.

---

## 11. Автозапуск через systemd (чтобы бот работал всегда)

Создайте службу:

```bash
sudo nano /etc/systemd/system/sub-tracker-bot.service
```

Вставьте (путь `/opt/sub-tracker-bot` при необходимости измените):

```ini
[Unit]
Description=Sub-Tracker Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sub-tracker-bot
Environment="PATH=/opt/sub-tracker-bot/venv/bin"
ExecStart=/opt/sub-tracker-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Сохраните и выполните:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sub-tracker-bot
sudo systemctl start sub-tracker-bot
sudo systemctl status sub-tracker-bot
```

В `status` должно быть `active (running)`. Логи:

```bash
sudo journalctl -u sub-tracker-bot -f
```

---

## 12. Полезные команды

| Действие              | Команда |
|-----------------------|--------|
| Статус бота           | `sudo systemctl status sub-tracker-bot` |
| Перезапуск            | `sudo systemctl restart sub-tracker-bot` |
| Остановка             | `sudo systemctl stop sub-tracker-bot` |
| Логи в реальном времени | `sudo journalctl -u sub-tracker-bot -f` |

---

## 13. Обновление бота после изменений кода

При загрузке через Git:

```bash
cd /opt/sub-tracker-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sub-tracker-bot
```

При загрузке архивом/SCP — снова скопируйте файлы в `/opt/sub-tracker-bot`, затем:

```bash
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sub-tracker-bot
```

---

## Краткий чеклист

- [ ] Сервер Timeweb создан (Ubuntu 22.04).
- [ ] Установлены: Python 3, venv, PostgreSQL, git.
- [ ] Созданы пользователь и БД PostgreSQL.
- [ ] Проект загружен в `/opt/sub-tracker-bot`.
- [ ] Создано venv и установлены зависимости.
- [ ] Файл `.env` с `BOT_TOKEN` и `DATABASE_URL`.
- [ ] Таблицы в БД созданы.
- [ ] Ручной запуск `python bot.py` успешен.
- [ ] Служба systemd включена и запущена.
- [ ] Бот отвечает в Telegram.

После этого бот будет работать онлайн на Timeweb постоянно.

---

## 14. Выкладка сайта Subboy на сервер

Сайт Subboy — это API (FastAPI) + статика React (subboy). Та же БД и бот.

### 14.1. Сборка фронта (на своём ПК)

На Windows в папке проекта:

```powershell
cd C:\Users\evil-\sub-tracker-bot\subboy
npm install
npm run build
```

Появится папка **subboy/dist** — её нужно загрузить на сервер в `/opt/sub-tracker-bot/subboy/dist`.

### 14.2. Загрузка на сервер

**Вариант А — SCP с ПК (после сборки):**

```powershell
scp -r C:\Users\evil-\sub-tracker-bot\subboy\dist root@ВАШ_IP:/opt/sub-tracker-bot/subboy/
```

**Вариант Б — на сервере:** если на сервере есть Node.js и npm:

```bash
cd /opt/sub-tracker-bot/subboy
npm install
npm run build
```

### 14.3. Зависимости API на сервере

В проекте уже есть FastAPI и uvicorn в `requirements.txt`. На сервере:

```bash
cd /opt/sub-tracker-bot
source venv/bin/activate
pip install -r requirements.txt
```

### 14.4. Запуск API (сайт Subboy)

**Вручную (проверка):**

```bash
cd /opt/sub-tracker-bot
source venv/bin/activate
uvicorn web.main:app --host 0.0.0.0 --port 8000
```

Откройте в браузере **http://ВАШ_IP:8000** — должен открыться Subboy. Остановка: **Ctrl+C**.

### 14.5. Автозапуск API через systemd

Чтобы сайт работал постоянно:

```bash
sudo nano /etc/systemd/system/sub-tracker-api.service
```

Вставьте (путь при необходимости измените):

```ini
[Unit]
Description=Subboy API (сайт + API)
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sub-tracker-bot
Environment="PATH=/opt/sub-tracker-bot/venv/bin"
ExecStart=/opt/sub-tracker-bot/venv/bin/uvicorn web.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Сохраните (**Ctrl+O**, Enter, **Ctrl+X**), затем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sub-tracker-api
sudo systemctl start sub-tracker-api
sudo systemctl status sub-tracker-api
```

Логи API: `sudo journalctl -u sub-tracker-api -f`.

### 14.6. HTTPS и домен (по желанию)

Чтобы открывать сайт по **https://ваш-домен.ru**:

1. Настройте DNS: A-запись домена → IP сервера.
2. Установите Nginx и Certbot:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx -y
   ```
3. Настройте Nginx как reverse proxy на порт 8000 и получите сертификат:
   ```bash
   sudo nano /etc/nginx/sites-available/subboy
   ```
   Пример конфига (замените `subboy.example.com` на свой домен):
   ```nginx
   server {
       listen 80;
       server_name subboy.example.com;
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
   ```bash
   sudo ln -s /etc/nginx/sites-available/subboy /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   sudo certbot --nginx -d subboy.example.com
   ```

После этого сайт будет доступен по **https://ваш-домен.ru**, кнопка «Login with Telegram» будет работать (Telegram принимает HTTPS-домен).
