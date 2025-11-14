from aiogram import Router, F
from aiogram.types import Message, Document, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.utils.db_utils import UserRepository, AccountRepository, LogRepository
from app.utils.keyboards import get_user_main_keyboard, get_confirm_keyboard
from app.utils.helpers import get_current_month, get_user_upload_dir, format_user_info
from config import UPLOAD_DIR, ADMIN_IDS

user_router = Router()


class UserStates(StatesGroup):
    """Состояния для пользователя"""
    waiting_for_account = State()
    waiting_for_wallet = State()


@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик команды /start"""
    user = await UserRepository.get_or_create_user(
        session, message.from_user.id, message.from_user.username
    )

    # Если пользователь новый (только создан) - отправить уведомление администратору
    if not user.access:
        # Отправить уведомление админам о новом пользователе
        for admin_id in ADMIN_IDS:
            try:
                admin_message = (
                    f"👤 *Новый пользователь*\n\n"
                    f"ID: {user.tg_id}\n"
                    f"Username: @{user.username or 'не указан'}\n\n"
                    f"Для разрешения доступа используйте команду:"
                    f"\n`/allow_user {user.tg_id}`"
                    f"\n\nДля запрещения доступа:"
                    f"\n`/deny_user {user.tg_id}`"
                )
                # Это будет отправлено в admin handlers
            except:
                pass

        await message.answer(
            "❌ У вас нет доступа к этому боту\n\n"
            "Администратор будет уведомлен о вашей попытке входа."
        )
        await LogRepository.create_log(
            session, "user_access_denied_attempt", user.id,
            description=f"User {user.tg_id} tried to access bot"
        )
        return

    # Отправить приветствие и главное меню
    await message.answer(
        f"👋 Добро пожаловать!\n\n"
        f"Ваш ID: {user.tg_id}\n"
        f"Username: @{user.username or 'не указан'}\n\n"
        f"Выберите действие:",
        reply_markup=get_user_main_keyboard()
    )
    await LogRepository.create_log(session, "user_start", user.id)


@user_router.message(F.text == "📤 Отправить аккаунт")
async def send_account(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик кнопки отправки аккаунта"""
    user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)

    if not user or not user.access:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    await message.answer(
        "📤 Отправьте архив\n\n"
        "Пожалуйста, загрузите архив с аккаунтом.\n"
        "Поддерживаемые форматы: ZIP, RAR, 7Z, TAR.GZ"
    )
    await state.set_state(UserStates.waiting_for_account)


@user_router.message(UserStates.waiting_for_account, F.document)
async def handle_account_upload(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик загрузки архива"""
    user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)

    if not user or not user.access:
        await message.answer("❌ У вас нет доступа.")
        return

    document = message.document
    # Проверить расширение файла
    allowed_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz']
    file_ext = Path(document.file_name).suffix.lower()

    if file_ext not in allowed_extensions:
        await message.answer(
            f"❌ Неподдерживаемый формат файла\n\n"
            f"Расширение {file_ext} не поддерживается.\n\n"
            f"Поддерживаемые форматы: {', '.join(allowed_extensions)}"
        )
        return

    # Загрузить файл
    from aiogram import Bot
    from config import BOT_TOKEN

    bot = Bot(token=BOT_TOKEN)
    user_dir = get_user_upload_dir(user.id)
    file_path = user_dir / document.file_name

    try:
        await bot.download(document, destination=str(file_path))

        # Сохранить информацию в БД
        month = get_current_month()
        account = await AccountRepository.create_account(
            session, user.id, str(file_path), month
        )

        await message.answer(
            f"✅ Архив успешно загружен\n\n"
            f"📁 Файл: {document.file_name}\n"
            f"📅 Месяц: {month}\n"
            f"🆔 ID архива: {account.id}"
        )

        # Отправить уведомление администратору
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"📤 Новый архив от пользователя\n\n"
                    f"👤 Username: @{user.username or 'не указан'}\n"
                    f"🆔 User ID: {user.tg_id}\n"
                    f"📁 Файл: {document.file_name}\n"
                    f"📅 Месяц: {month}\n"
                    f"🆔 Account ID: {account.id}"
                )
            except:
                pass

        await LogRepository.create_log(
            session, "account_uploaded", user.id,
            description=f"File: {document.file_name}, Account ID: {account.id}"
        )

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при загрузке файла\n\n"
            f"Пожалуйста, попробуйте еще раз.\n\n"
            f"Ошибка: {str(e)}"
        )

    await state.clear()
    await message.answer(
        "Выберите действие:",
        reply_markup=get_user_main_keyboard()
    )


@user_router.message(F.text == "🌐 Запросить прокси")
async def request_proxy(message: Message, session: AsyncSession):
    """Обработчик запроса прокси"""
    user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)

    if not user or not user.access:
        await message.answer("❌ У вас нет доступа.")
        return

    await message.answer(
        "📤 Ваш запрос отправлен администратору\n\n"
        "Вы запросили прокси. Администратор получит ваш запрос и ответит вам.",
        reply_markup=get_user_main_keyboard()
    )

    # Отправить уведомление администратору
    from aiogram import Bot
    from config import BOT_TOKEN

    bot = Bot(token=BOT_TOKEN)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🌐 Запрос прокси\n\n"
                f"👤 Username: @{user.username or 'не указан'}\n"
                f"🆔 User ID: {user.tg_id}"
            )
        except:
            pass

    await LogRepository.create_log(session, "proxy_requested", user.id)


@user_router.message(F.text == "📱 Запросить номера")
async def request_numbers(message: Message, session: AsyncSession):
    """Обработчик запроса номеров"""
    user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)

    if not user or not user.access:
        await message.answer("❌ У вас нет доступа.")
        return

    await message.answer(
        "📤 Ваш запрос отправлен администратору\n\n"
        "Вы запросили номера. Администратор получит ваш запрос и ответит вам.",
        reply_markup=get_user_main_keyboard()
    )

    # Отправить уведомление администратору
    from aiogram import Bot
    from config import BOT_TOKEN

    bot = Bot(token=BOT_TOKEN)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📱 Запрос номеров (DaisySMS)\n\n"
                f"👤 Username: @{user.username or 'не указан'}\n"
                f"🆔 User ID: {user.tg_id}"
            )
        except:
            pass

    await LogRepository.create_log(session, "numbers_requested", user.id)


@user_router.message(F.text == "💳 Прикрепить TRX-кошелек")
async def attach_wallet(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик прикрепления TRX-кошелька"""
    user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)

    if not user or not user.access:
        await message.answer("❌ У вас нет доступа.")
        return

    current_wallet = user.trx_wallet or "Не установлен"
    await message.answer(
        f"💳 Прикрепить TRX-кошелек\n\n"
        f"Текущий кошелек: {current_wallet}\n\n"
        f"Введите адрес вашего TRX-кошелька:"
    )
    await state.set_state(UserStates.waiting_for_wallet)


@user_router.message(UserStates.waiting_for_wallet)
async def save_wallet(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранить TRX-кошелек"""
    wallet = message.text.strip()

    if len(wallet) < 30 or len(wallet) > 40:
        await message.answer(
            "❌ Неверный формат адреса\n\n"
            "TRX адрес должен быть в формате: TNXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n\n"
            "Попробуйте еще раз:"
        )
        return

    user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)
    await UserRepository.update_user_wallet(session, message.from_user.id, wallet)

    await message.answer(
        f"✅ TRX-кошелек успешно сохранен\n\n"
        f"Адрес: {wallet}",
        reply_markup=get_user_main_keyboard()
    )

    await LogRepository.create_log(
        session, "wallet_attached", user.id, description=f"Wallet: {wallet}"
    )

    await state.clear()
