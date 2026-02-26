@echo off
echo Создание базы данных sub_tracker...
echo.
echo Введите пароль от PostgreSQL (пользователь postgres):
psql -U postgres -c "CREATE DATABASE sub_tracker;"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ База данных sub_tracker успешно создана!
) else (
    echo.
    echo ❌ Ошибка при создании базы данных.
    echo Попробуйте создать вручную через pgAdmin или командную строку.
)
pause
