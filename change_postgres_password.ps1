# Скрипт для изменения пароля PostgreSQL
Write-Host "Изменение пароля пользователя postgres..." -ForegroundColor Green
Write-Host ""

# Попробуем найти psql
$psqlPath = $null
$possiblePaths = @(
    "C:\Program Files\PostgreSQL\18\bin\psql.exe",
    "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files\PostgreSQL\15\bin\psql.exe",
    "C:\Program Files\PostgreSQL\14\bin\psql.exe"
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
    Write-Host "Используйте pgAdmin для изменения пароля:" -ForegroundColor Yellow
    Write-Host "1. Откройте pgAdmin" -ForegroundColor Yellow
    Write-Host "2. Правой кнопкой на сервере PostgreSQL → Properties" -ForegroundColor Yellow
    Write-Host "3. Вкладка 'Connection' → измените пароль" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit
}

Write-Host "Найден psql: $psqlPath" -ForegroundColor Green
Write-Host ""
Write-Host "Введите ТЕКУЩИЙ пароль от PostgreSQL:" -ForegroundColor Yellow
$currentPassword = Read-Host -AsSecureString
$BSTR1 = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($currentPassword)
$plainCurrentPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR1)

Write-Host ""
Write-Host "Введите НОВЫЙ пароль:" -ForegroundColor Yellow
$newPassword = Read-Host -AsSecureString
$BSTR2 = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($newPassword)
$plainNewPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR2)

Write-Host ""
Write-Host "Подтвердите новый пароль:" -ForegroundColor Yellow
$confirmPassword = Read-Host -AsSecureString
$BSTR3 = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($confirmPassword)
$plainConfirmPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR3)

if ($plainNewPassword -ne $plainConfirmPassword) {
    Write-Host ""
    Write-Host "❌ Пароли не совпадают!" -ForegroundColor Red
    pause
    exit
}

$env:PGPASSWORD = $plainCurrentPassword

Write-Host ""
Write-Host "Изменение пароля..." -ForegroundColor Cyan

# Экранируем специальные символы в пароле для SQL
$escapedPassword = $plainNewPassword -replace "'", "''"

$sqlCommand = "ALTER USER postgres WITH PASSWORD '$escapedPassword';"
& $psqlPath -U postgres -c $sqlCommand 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Пароль успешно изменен!" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  Не забудьте обновить файл .env с новым паролем!" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ Ошибка при изменении пароля." -ForegroundColor Red
    Write-Host "Возможно, текущий пароль неверный." -ForegroundColor Yellow
}

$env:PGPASSWORD = $null
Write-Host ""
pause
