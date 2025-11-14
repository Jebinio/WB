@echo off
REM Script for initializing and running the Telegram Bot on Windows

echo ==========================================
echo Telegram Bot - Setup and Initialization
echo ==========================================

REM Check Python version
python --version

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file and add your BOT_TOKEN
    echo Then run: python main.py
) else (
    echo .env file already exists
)

echo ==========================================
echo Setup complete!
echo Run: python main.py
echo ==========================================
pause
