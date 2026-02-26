# Проверка базы данных через psql
Write-Host "Проверка базы данных sub_tracker..." -ForegroundColor Cyan
Write-Host ""

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

if ($null -eq $psqlPath) {
    Write-Host "[ERROR] psql.exe не найден" -ForegroundColor Red
    Write-Host "Проверьте через pgAdmin:" -ForegroundColor Yellow
    Write-Host "  1. Откройте pgAdmin" -ForegroundColor White
    Write-Host "  2. Посмотрите список баз данных" -ForegroundColor White
    Write-Host "  3. Должна быть база данных 'sub_tracker'" -ForegroundColor White
    pause
    exit
}

Write-Host "Найден psql: $psqlPath" -ForegroundColor Green
Write-Host ""
Write-Host "Введите пароль от PostgreSQL:" -ForegroundColor Yellow
$password = Read-Host -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

$env:PGPASSWORD = $plainPassword

Write-Host ""
Write-Host "Проверка существования базы данных..." -ForegroundColor Cyan
$result = & $psqlPath -U postgres -lqt 2>&1 | Select-String "sub_tracker"

if ($result) {
    Write-Host "[OK] База данных sub_tracker существует!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Проверка таблиц..." -ForegroundColor Cyan
    $tables = & $psqlPath -U postgres -d sub_tracker -c "\dt" 2>&1
    
    if ($tables -match "Did not find any relations") {
        Write-Host "[WARNING] Таблицы не найдены!" -ForegroundColor Yellow
        Write-Host "Запустите: python init_db.py" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Таблицы найдены:" -ForegroundColor Green
        $tables | Select-String "public" | ForEach-Object {
            Write-Host "  $_" -ForegroundColor White
        }
    }
} else {
    Write-Host "[ERROR] База данных sub_tracker НЕ найдена!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Создайте базу данных:" -ForegroundColor Yellow
    Write-Host "  1. Откройте pgAdmin" -ForegroundColor White
    Write-Host "  2. Правой кнопкой на 'Databases' -> Create -> Database" -ForegroundColor White
    Write-Host "  3. Имя: sub_tracker" -ForegroundColor White
    Write-Host "  4. Save" -ForegroundColor White
}

$env:PGPASSWORD = $null
Write-Host ""
pause
