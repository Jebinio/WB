@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo.
echo ================================================
echo Запуск Telegram Bot
echo ================================================
echo.
echo Проверка наличия файла .env...
if not exist .env (
    echo ERROR: Файл .env не найден!
    echo Пожалуйста, отредактируйте файл .env перед запуском
    echo.
    echo 1. Откройте файл .env
    echo 2. Замените YOUR_BOT_TOKEN_HERE на ваш токен
    echo 3. Замените YOUR_TELEGRAM_ID_HERE на ваш ID
    echo.
    pause
    exit /b 1
)
echo OK - Файл .env найден
echo.
echo Запуск бота...
python main.py
pause
