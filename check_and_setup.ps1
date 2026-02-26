# Скрипт для проверки и настройки
Write-Host "🔍 Проверка настроек бота..." -ForegroundColor Cyan
Write-Host ""

# Проверяем .env файл
$envContent = Get-Content ".env" -Raw
if ($envContent -match "ваш_пароль") {
    Write-Host "⚠️  ВНИМАНИЕ: В файле .env все еще указан 'ваш_пароль'!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Нужно заменить на реальный пароль от PostgreSQL." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Откройте файл .env и замените:" -ForegroundColor White
    Write-Host "  DATABASE_URL=postgresql+asyncpg://postgres:ваш_пароль@localhost:5432/sub_tracker" -ForegroundColor Gray
    Write-Host ""
    Write-Host "На:" -ForegroundColor White
    Write-Host "  DATABASE_URL=postgresql+asyncpg://postgres:ВАШ_РЕАЛЬНЫЙ_ПАРОЛЬ@localhost:5432/sub_tracker" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Нажмите любую клавишу после того, как обновите .env файл..." -ForegroundColor Yellow
    pause
}

# Проверяем наличие базы данных
Write-Host ""
Write-Host "Проверка базы данных..." -ForegroundColor Cyan

$psqlPath = $null
$possiblePaths = @(
    "C:\Program Files\PostgreSQL\18\bin\psql.exe",
    "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    "C:\Program Files\PostgreSQL\16\bin\psql.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $psqlPath = $path
        break
    }
}

if ($null -ne $psqlPath) {
    Write-Host "Найден psql: $psqlPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "Хотите создать базу данных sub_tracker? (Y/N)" -ForegroundColor Yellow
    $create = Read-Host
    
    if ($create -eq "Y" -or $create -eq "y") {
        Write-Host ""
        Write-Host "Введите пароль от PostgreSQL:" -ForegroundColor Yellow
        $password = Read-Host -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
        $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        
        $env:PGPASSWORD = $plainPassword
        
        Write-Host ""
        Write-Host "Создание базы данных..." -ForegroundColor Cyan
        & $psqlPath -U postgres -c "CREATE DATABASE sub_tracker;" 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ База данных sub_tracker создана!" -ForegroundColor Green
        } else {
            Write-Host "⚠️  База данных уже существует или произошла ошибка." -ForegroundColor Yellow
        }
        
        $env:PGPASSWORD = $null
    }
} else {
    Write-Host "⚠️  psql не найден. Создайте базу данных через pgAdmin:" -ForegroundColor Yellow
    Write-Host "   1. Откройте pgAdmin" -ForegroundColor White
    Write-Host "   2. Правой кнопкой на 'Databases' → Create → Database" -ForegroundColor White
    Write-Host "   3. Имя: sub_tracker" -ForegroundColor White
}

Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
Write-Host "   1. Убедитесь, что база данных sub_tracker создана" -ForegroundColor White
Write-Host "   2. Обновите .env файл с правильным паролем" -ForegroundColor White
Write-Host "   3. Запустите: python init_db.py" -ForegroundColor White
Write-Host "   4. Запустите: python bot.py" -ForegroundColor White
Write-Host ""
pause
