# Как запустить PostgreSQL

## ✅ Хорошие новости!

PostgreSQL уже запущен на вашем компьютере! 
Служба: `postgresql-x64-18` - **Running** (работает)

## Способы управления PostgreSQL:

### 1. Через службы Windows (Services)

1. Нажмите `Win + R`
2. Введите `services.msc` и нажмите Enter
3. Найдите службу `postgresql-x64-18` (или похожую с "PostgreSQL")
4. Правой кнопкой → **Start** (Запустить) или **Stop** (Остановить)

### 2. Через PowerShell (от имени администратора)

**Запустить:**
```powershell
Start-Service postgresql-x64-18
```

**Остановить:**
```powershell
Stop-Service postgresql-x64-18
```

**Проверить статус:**
```powershell
Get-Service postgresql-x64-18
```

### 3. Через командную строку (от имени администратора)

**Запустить:**
```cmd
net start postgresql-x64-18
```

**Остановить:**
```cmd
net stop postgresql-x64-18
```

## Следующие шаги:

Теперь, когда PostgreSQL запущен, нужно:

1. **Создать базу данных** (см. QUICK_START.md)
2. **Настроить .env файл** с паролем
3. **Установить зависимости Python**
4. **Запустить бота**
