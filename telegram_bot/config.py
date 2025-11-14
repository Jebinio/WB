import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузить переменные окружения
load_dotenv()

# Пути
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "bot.db"

# Создать папки если их нет
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Конфигурация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в файле .env")

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

# Admin IDs (разделены запятыми в .env)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(aid.strip()) for aid in ADMIN_IDS_STR.split(",") if aid.strip()]

# Путь для сохранения архивов
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "data/uploads")

# Время хранения архивов (в днях)
ARCHIVE_RETENTION_DAYS = 30
