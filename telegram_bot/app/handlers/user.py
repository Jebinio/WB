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
    waiting_for_shift_time = State()
    waiting_for_shift_close = State()


@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик команды /start"""
    # Проверить существует ли пользователь
    existing_user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)
    is_new_user = existing_user is None
    
    user = await UserRepository.get_or_create_user(
        session, message.from_user.id, message.from_user.first_name
    )

    # Если пользователь без доступа
    if not user.access:
        # Если пользователь новый - отправить уведомление администратору
        if is_new_user:
            # Отправить уведомление админам о новом пользователе
            from aiogram import Bot
            from config import BOT_TOKEN
            from app.utils.keyboards import get_new_user_approval_keyboard
            bot = Bot(token=BOT_TOKEN)
            
            username_display = f"@{user.username}" if user.username else "не указано"
            
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"👤 Новый пользователь\n\n"
                        f"ID: {user.tg_id}\n"
                        f"Имя: {username_display}\n\n"
                        f"Разрешить доступ?",
                        reply_markup=get_new_user_approval_keyboard(user.id)
                    )
                except:
                    pass

        # Отправить пользователю сообщение об отказе
        await message.answer(
            "❌ Вам отказано в доступе к боту.\n\n"
            "Свяжитесь с администратором для получения дополнительной информации."
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
        f"Имя: {user.username or 'не указано'}\n\n"
        f"Выберите действие:",
        reply_markup=get_user_main_keyboard(is_admin=message.from_user.id in ADMIN_IDS)
    )
    await LogRepository.create_log(session, "user_start", user.id)


@user_router.callback_query(F.data == "user_send_account")
async def send_account(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработчик кнопки отправки аккаунта"""
    user = await UserRepository.get_user_by_tg_id(session, callback.from_user.id)

    if not user or not user.access:
        await callback.answer("❌ У вас нет доступа к этому боту.", show_alert=True)
        return

    await callback.message.edit_text(
        "📤 Отправьте архив\n\n"
        "Пожалуйста, загрузите архив с аккаунтом.\n"
        "Поддерживаемые форматы: ZIP, RAR, 7Z, TAR.GZ"
    )
    await state.set_state(UserStates.waiting_for_account)
    await callback.answer()


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

        # Сохранить информацию в БД (только имя файла)
        month = get_current_month()
        account = await AccountRepository.create_account(
            session, user.id, document.file_name, month
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


@user_router.callback_query(F.data == "user_request_proxy")
async def request_proxy(callback: CallbackQuery, session: AsyncSession):
    """Обработчик запроса прокси"""
    user = await UserRepository.get_user_by_tg_id(session, callback.from_user.id)

    if not user or not user.access:
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.message.edit_text(
        "📤 Ваш запрос отправлен администратору\n\n"
        "Вы запросили прокси. Администратор получит ваш запрос и ответит вам.",
        reply_markup=get_user_main_keyboard(is_admin=callback.from_user.id in ADMIN_IDS)
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
    await callback.answer()


@user_router.callback_query(F.data == "user_open_shift")
async def open_shift_request(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать процесс открытия смены: запросить время по МСК"""
    user = await UserRepository.get_user_by_tg_id(session, callback.from_user.id)

    if not user or not user.access:
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.message.edit_text(
        "🕒 Открыть смену\n\n"
        "Введите желаемое время в формате HH:MM (по МСК), например: 09:30"
    )
    await state.set_state(UserStates.waiting_for_shift_time)
    await callback.answer()


@user_router.message(UserStates.waiting_for_shift_time)
async def handle_shift_time(message: Message, state: FSMContext, session: AsyncSession):
    """Обработать введенное время и отправить уведомление админам"""
    user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)

    if not user or not user.access:
        await message.answer("❌ У вас нет доступа.")
        await state.clear()
        return

    time_text = message.text.strip()

    # Простейшая валидация формата HH:MM
    import re
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", time_text):
        await message.answer(
            "❌ Неверный формат времени. Пожалуйста, введите в формате HH:MM (например: 09:30)."
        )
        return

    # Отправить уведомление администраторам
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🕒 Открытие смены\n\n"
                f"Пользователь: {user.username or 'не указано'}\n"
                f"TG ID: {user.tg_id}\n"
                f"Время (МСК): {time_text}"
            )
        except:
            pass

    await LogRepository.create_log(
        session, "shift_requested", user.id, description=f"Shift at {time_text} MSK"
    )

    await message.answer(
        f"✅ Запрос отправлен администраторам. Вы записаны на смену в {time_text} МСК.",
        reply_markup=get_user_main_keyboard(is_admin=message.from_user.id in ADMIN_IDS)
    )

    await state.clear()



@user_router.callback_query(F.data == "user_close_shift")
async def close_shift_request(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать процесс закрытия смены: запросить время и количество аккаунтов"""
    user = await UserRepository.get_user_by_tg_id(session, callback.from_user.id)

    if not user or not user.access:
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.message.edit_text(
        "🔒 Закрыть смену\n\n"
        "Введите время и количество аккаунтов в формате: HH:MM <количество>\n"
        "Пример: 18:00 12"
    )
    await state.set_state(UserStates.waiting_for_shift_close)
    await callback.answer()


@user_router.message(UserStates.waiting_for_shift_close)
async def handle_shift_close(message: Message, state: FSMContext, session: AsyncSession):
    """Обработать закрытие смены: парсинг времени и количества, отправка админу"""
    user = await UserRepository.get_user_by_tg_id(session, message.from_user.id)

    if not user or not user.access:
        await message.answer("❌ У вас нет доступа.")
        await state.clear()
        return

    text = message.text.strip()
    import re
    m = re.match(r"^(?:([01]\d|2[0-3]):([0-5]\d))\s+(\d+)$", text)
    if not m:
        await message.answer(
            "❌ Неверный формат. Введите в формате: HH:MM <количество> (например: 18:00 12)"
        )
        return

    time_text = f"{m.group(1)}:{m.group(2)}"
    reported_count = int(m.group(3))

    # Получить реальное количество аккаунтов пользователя
    accounts = await AccountRepository.get_accounts_by_user(session, user.id)
    actual_count = len(accounts)

    # Отправить уведомление администраторам
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔒 Закрытие смены\n\n"
                f"Пользователь: {user.username or 'не указано'}\n"
                f"TG ID: {user.tg_id}\n"
                f"Время (МСК): {time_text}\n"
                f"Количество (отправлено пользователем): {reported_count}\n"
                f"Количество (реально загружено): {actual_count}"
            )
        except:
            pass

    await LogRepository.create_log(
        session, "shift_closed", user.id,
        description=f"Shift closed at {time_text} MSK, reported={reported_count}, actual={actual_count}"
    )

    await message.answer(
        f"✅ Закрытие смены отправлено администраторам. Время: {time_text}. Количество: {reported_count} (реально {actual_count}).",
        reply_markup=get_user_main_keyboard(is_admin=message.from_user.id in ADMIN_IDS)
    )

    await state.clear()


@user_router.callback_query(F.data == "user_request_numbers")
async def request_numbers(callback: CallbackQuery, session: AsyncSession):
    """Обработчик запроса номеров"""
    user = await UserRepository.get_user_by_tg_id(session, callback.from_user.id)

    if not user or not user.access:
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.message.edit_text(
        "📤 Ваш запрос отправлен администратору\n\n"
        "Вы запросили номера. Администратор получит ваш запрос и ответит вам.",
        reply_markup=get_user_main_keyboard(is_admin=callback.from_user.id in ADMIN_IDS)
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
    await callback.answer()


@user_router.callback_query(F.data == "user_attach_wallet")
async def attach_wallet(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработчик прикрепления TRX-кошелька"""
    user = await UserRepository.get_user_by_tg_id(session, callback.from_user.id)

    if not user or not user.access:
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    current_wallet = user.trx_wallet or "Не установлен"
    await callback.message.edit_text(
        f"💳 Прикрепить TRX-кошелек\n\n"
        f"Текущий кошелек: {current_wallet}\n\n"
        f"Введите адрес вашего TRX-кошелька:"
    )
    await state.set_state(UserStates.waiting_for_wallet)
    await callback.answer()


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
        reply_markup=get_user_main_keyboard(is_admin=message.from_user.id in ADMIN_IDS)
    )

    await LogRepository.create_log(
        session, "wallet_attached", user.id, description=f"Wallet: {wallet}"
    )

    await state.clear()


@user_router.callback_query(F.data == "user_main_menu")
async def user_main_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню пользователя"""
    await state.clear()
    try:
        await callback.message.edit_text(
            "👨‍💼 Главное меню\n\n"
            "Выберите действие:",
            reply_markup=get_user_main_keyboard(is_admin=callback.from_user.id in ADMIN_IDS)
        )
    except Exception:
        pass
    await callback.answer()


@user_router.callback_query(F.data == "user_to_admin_panel")
async def user_to_admin_panel(callback: CallbackQuery, session: AsyncSession):
    """Переключиться на админ панель"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет доступа к админ панели.", show_alert=True)
        return

    from app.utils.keyboards import get_admin_main_keyboard
    
    try:
        await callback.message.edit_text(
            "👨‍💼 Панель администратора\n\n"
            "Выберите действие:",
            reply_markup=get_admin_main_keyboard()
        )
    except Exception:
        pass
    await callback.answer()
