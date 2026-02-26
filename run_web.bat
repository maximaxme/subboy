@echo off
REM Запуск API и сайта subboy (тот же бэк, что и бот)
cd /d "%~dp0"
call venv\Scripts\activate 2>nul || python -m venv venv && call venv\Scripts\activate
uvicorn web.main:app --host 0.0.0.0 --port 8000
