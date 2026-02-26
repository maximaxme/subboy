# Скрипт для создания базы данных
Write-Host "Создание базы данных sub_tracker..." -ForegroundColor Green
Write-Host ""

# Попробуем найти psql
$psqlPath = $null
$possiblePaths = @(
    "C:\Program Files\PostgreSQL\18\bin\psql.exe",
    "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files\PostgreSQL\15\bin\psql.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $psqlPath = $path
        break
    }
}

if ($null -eq $psqlPath) {
    Write-Host "❌ Не найден psql.exe" -ForegroundColor Red
    Write-Host ""
    Write-Host "Создайте базу данных вручную:" -ForegroundColor Yellow
    Write-Host "1. Откройте pgAdmin (из меню Пуск)" -ForegroundColor Yellow
    Write-Host "2. Подключитесь к серверу PostgreSQL" -ForegroundColor Yellow
    Write-Host "3. Правой кнопкой на 'Databases' → Create → Database" -ForegroundColor Yellow
    Write-Host "4. Имя: sub_tracker" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit
}

Write-Host "Найден psql: $psqlPath" -ForegroundColor Green
Write-Host ""
Write-Host "Введите пароль от PostgreSQL (пользователь postgres):" -ForegroundColor Yellow
$password = Read-Host -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

$env:PGPASSWORD = $plainPassword

Write-Host ""
Write-Host "Создание базы данных..." -ForegroundColor Cyan

& $psqlPath -U postgres -c "CREATE DATABASE sub_tracker;" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ База данных sub_tracker успешно создана!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠️  Возможно, база данных уже существует или произошла ошибка." -ForegroundColor Yellow
    Write-Host "Проверьте подключение и попробуйте создать вручную через pgAdmin." -ForegroundColor Yellow
}

$env:PGPASSWORD = $null
Write-Host ""
pause
