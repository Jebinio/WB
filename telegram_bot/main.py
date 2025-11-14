"""
Telegram Bot для управления аккаунтами и уведомлениями

Структура проекта:
- main.py: Точка входа приложения
- config.py: Конфигурация и переменные окружения
- app/models.py: Модели БД (User, Account, Log)
- app/handlers/: Обработчики команд
  - user.py: Обработчики для пользователей
  - admin.py: Обработчики для администраторов
- app/utils/: Утилиты
  - db_utils.py: Репозитории для работы с БД
  - keyboards.py: Клавиатуры и кнопки
  - helpers.py: Вспомогательные функции
- data/: Директория для данных
  - uploads/: Загруженные архивы
  - bot.db: База данных SQLite
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram.types import Message, Update

from config import BOT_TOKEN, ADMIN_IDS
from app.models import init_db, AsyncSessionLocal
from app.handlers.user import user_router
from app.handlers.admin import admin_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Middleware для подключения к БД к каждому запросу
class DatabaseMiddleware:
    """Middleware для добавления сессии БД в контекст обработчиков"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(self, handler, event, data):
        async with self.session_factory() as session:
            data['session'] = session
            return await handler(event, data)


async def main():
    """Главная функция запуска бота"""
    logger.info("=" * 70)
    logger.info("Запуск Telegram бота...")
    logger.info("=" * 70)

    # Проверка конфигурации
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в файле .env")
        return
    
    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS не установлены в файле .env")

    # Инициализация БД
    logger.info("Инициализация базы данных...")
    try:
        await init_db()
        logger.info("[OK] База данных инициализирована")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при инициализации БД: {e}")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация middleware для БД
    @dp.message.middleware()
    @dp.callback_query.middleware()
    async def database_middleware(handler, event, data):
        async with AsyncSessionLocal() as session:
            data['session'] = session
            return await handler(event, data)

    # Регистрация роутеров
    dp.include_router(user_router)
    dp.include_router(admin_router)

    logger.info("[OK] Бот инициализирован")
    logger.info(f"Администраторы: {ADMIN_IDS}")
    logger.info("=" * 70)
    logger.info("[START] Бот запущен и готов к работе")
    logger.info("=" * 70)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"[ERROR] Критическая ошибка: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("Подключение к боту закрыто")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при запуске: {e}", exc_info=True)
