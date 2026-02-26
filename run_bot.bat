@echo off
echo Запуск бота...
echo.
echo Останавливаем другие запущенные копии бота (если есть)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*bot.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul
echo.
python bot.py
pause
