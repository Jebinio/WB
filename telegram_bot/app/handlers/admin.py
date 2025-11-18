from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User, Account
from app.utils.db_utils import UserRepository, AccountRepository, LogRepository
from app.utils.keyboards import (
    get_admin_main_keyboard, get_accounts_view_keyboard, 
    get_notification_type_keyboard, get_notification_recipient_keyboard,
    get_account_actions_keyboard, get_confirm_keyboard, get_user_management_keyboard,
    get_new_user_approval_keyboard
)
from app.utils.helpers import (
    get_current_month, format_account_info, format_user_info,
    get_notification_text
)
from config import ADMIN_IDS
from config import BOT_TOKEN
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.types import FSInputFile
from datetime import datetime, timedelta
from pathlib import Path

admin_router = Router()


class AdminStates(StatesGroup):
    """Состояния для администратора"""
    waiting_for_notification_text = State()
    waiting_for_call_datetime = State()
    waiting_for_notification_recipient = State()
    waiting_for_user_id_manage = State()
    waiting_for_access_decision = State()
    waiting_for_user_manage_username = State()
    waiting_for_admin_username = State()
    waiting_for_numbers_response = State()
    waiting_for_numbers_recipient = State()
    waiting_for_proxy_response = State()
    waiting_for_custom_notification_text = State()


def is_admin(message_or_callback) -> bool:
    """Проверить, является ли пользователь администратором"""
    user_id = message_or_callback.from_user.id
    return user_id in ADMIN_IDS


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    """Админ панель"""
    if not is_admin(message):
        await message.answer("❌ У вас нет доступа к панели администратора.")
        return

    await message.answer(
        "👨‍💼 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_main_keyboard()
    )


@admin_router.callback_query(F.data == "admin_view_accounts")
async def view_accounts_menu(callback: CallbackQuery, session: AsyncSession):
    """Меню просмотра аккаунтов"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            "📋 Просмотр аккаунтов\n\n"
            "Выберите фильтр:",
            reply_markup=get_accounts_view_keyboard()
        )
    except Exception:
        # Если сообщение не изменилось, просто ответим на callback
        pass
    
    await callback.answer()


@admin_router.callback_query(F.data == "admin_manage_users")
async def manage_users_menu(callback: CallbackQuery, session: AsyncSession):
    """Меню управления пользователями"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    users = await UserRepository.get_all_users(session)
    allowed_count = sum(1 for u in users if u.access)
    blocked_count = len(users) - allowed_count

    try:
        await callback.message.edit_text(
            f"👥 Управление пользователями\n\n"
            f"📊 Статистика:\n"
            f"• Всего пользователей: {len(users)}\n"
            f"• С доступом: {allowed_count}\n"
            f"• Без доступа: {blocked_count}",
            reply_markup=get_user_management_keyboard()
        )
    except Exception:
        pass
    await callback.answer()


@admin_router.callback_query(F.data == "admin_send_notification")
async def send_notification_menu(callback: CallbackQuery, session: AsyncSession):
    """Меню отправки уведомления"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    kb_buttons = [
        [InlineKeyboardButton(text="💰 Зарплата выдана", callback_data="notify_salary")],
        [InlineKeyboardButton(text="📞 Назначен созвон", callback_data="notify_call")],
        [InlineKeyboardButton(text="⚠️ Назначен штраф", callback_data="notify_penalty")],
        [InlineKeyboardButton(text="📝 Кастомное уведомление", callback_data="notify_custom")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    try:
        await callback.message.edit_text(
            "📢 Отправить уведомление\n\n"
            "Выберите тип уведомления:",
            reply_markup=keyboard
        )
    except Exception:
        pass
    await callback.answer()


@admin_router.callback_query(F.data == "admin_respond_numbers")
async def respond_numbers_menu(callback: CallbackQuery, session: AsyncSession):
    """Меню ответа на запрос номеров"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    users = await UserRepository.get_all_users(session)
    if not users:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text("👥 Пользователи не найдены", reply_markup=keyboard)
        await callback.answer()
        return

    # Построить inline-клавиатуру со списком пользователей
    kb_buttons = []
    for u in users:
        label = f"{u.username or u.tg_id} ({u.tg_id})"
        kb_buttons.append([InlineKeyboardButton(text=label, callback_data=f"respond_numbers_user_{u.id}")])

    # добавить кнопку назад
    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(
        "📱 Выберите пользователя для отправки номеров:",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("numbers_sent_confirm_"))
async def numbers_sent_confirm(callback: CallbackQuery, session: AsyncSession):
    """Обработчик подтверждения пополнения номеров"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    # Обновить сообщение админа
    await callback.message.edit_text(
        f"📱 Запрос номеров (DaisySMS)\n\n"
        f"👤 Username: @{user.username or 'не указан'}\n"
        f"🆔 User ID: {user.tg_id}\n\n"
        f"✅ Сервис пополнен"
    )

    # Отправить уведомление пользователю о пополнении
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            user.tg_id,
            f"✅ Ваш запрос обработан\n\n"
            f"Администратор пополнил сервис аренды номеров для вашего аккаунта."
        )
    except:
        pass

    await LogRepository.create_log(
        session, "numbers_service_replenished", user.id, admin_id=callback.from_user.id
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("proxy_sent_confirm_"))
async def proxy_sent_confirm(callback: CallbackQuery, session: AsyncSession):
    """Обработчик подтверждения пополнения прокси"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    # Обновить сообщение админа
    await callback.message.edit_text(
        f"🌐 Запрос прокси\n\n"
        f"👤 Username: @{user.username or 'не указан'}\n"
        f"🆔 User ID: {user.tg_id}\n\n"
        f"✅ Прокси пополнены"
    )

    # Отправить уведомление пользователю о пополнении
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            user.tg_id,
            f"✅ Ваш запрос обработан\n\n"
            f"Администратор пополнил прокси для вашего аккаунта."
        )
    except:
        pass

    await LogRepository.create_log(
        session, "proxy_service_replenished", user.id, admin_id=callback.from_user.id
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("proxy_respond_"))
async def proxy_respond(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработчик кнопки ответа на запрос прокси"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    # Сохранить ID пользователя в состояние
    await state.update_data(proxy_respond_user_id=user.tg_id, proxy_respond_username=user.username)
    
    await callback.message.edit_text(
        f"💬 Ответить пользователю @{user.username}\n\n"
        f"Введите текст ответа:"
    )
    await state.set_state(AdminStates.waiting_for_proxy_response)
    await callback.answer()



@admin_router.callback_query(F.data.startswith("numbers_respond_"))
async def numbers_respond(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработчик кнопки ответа на запрос номеров"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    # Сохранить ID пользователя в состояние
    await state.update_data(numbers_respond_user_id=user.tg_id, numbers_respond_username=user.username)
    
    await callback.message.edit_text(
        f"💬 Ответить пользователю @{user.username}\n\n"
        f"Введите текст ответа:"
    )
    await state.set_state(AdminStates.waiting_for_numbers_response)
    await callback.answer()



@admin_router.callback_query(F.data.startswith("respond_numbers_user_"))
async def respond_numbers_user_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбран пользователь для отправки номеров"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Некорректный пользователь.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    # Сохранить ID пользователя в состояние
    await state.update_data(numbers_recipient_id=user.tg_id, numbers_recipient_username=user.username)
    
    await callback.message.edit_text(
        f"📱 Пополнить сервис аренды номеров для @{user.username}\n\n"
        f"Введите информацию или комментарий для пользователя:"
    )
    await state.set_state(AdminStates.waiting_for_numbers_response)
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_numbers_response)
async def handle_numbers_input(message: Message, state: FSMContext, session: AsyncSession):
    """Обработать пополнение сервиса и отправить уведомление пользователю"""
    if not is_admin(message):
        await message.answer("❌ У вас нет доступа.")
        await state.clear()
        return

    response_text = message.text.strip()
    data = await state.get_data()
    
    # Проверяем, откуда был вызван ввод (из меню или из кнопки)
    recipient_id = data.get("numbers_respond_user_id") or data.get("numbers_recipient_id")
    recipient_username = data.get("numbers_respond_username") or data.get("numbers_recipient_username")

    if not response_text:
        await message.answer("❌ Текст не введен. Пожалуйста, попробуйте еще раз.")
        return

    # Отправить ответ пользователю
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)

    try:
        await bot.send_message(
            recipient_id,
            f"✅ Ответ администратора\n\n"
            f"{response_text}"
        )
        
        await message.answer(
            f"✅ Ответ отправлен пользователю @{recipient_username}"
        )
        
        await LogRepository.create_log(
            session, "numbers_response_sent", recipient_id, 
            admin_id=message.from_user.id,
            description=f"Response: {response_text}"
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при отправке ответа\n\n"
            f"Ошибка: {str(e)}"
        )

    await state.clear()
    await message.answer(
        "👨‍💼 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_main_keyboard()
    )


@admin_router.message(AdminStates.waiting_for_proxy_response)
async def handle_proxy_input(message: Message, state: FSMContext, session: AsyncSession):
    """Обработать ответ на запрос прокси"""
    if not is_admin(message):
        await message.answer("❌ У вас нет доступа.")
        await state.clear()
        return

    response_text = message.text.strip()
    data = await state.get_data()
    
    recipient_id = data.get("proxy_respond_user_id")
    recipient_username = data.get("proxy_respond_username")

    if not response_text:
        await message.answer("❌ Текст не введен. Пожалуйста, попробуйте еще раз.")
        return

    # Отправить ответ пользователю
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)

    try:
        await bot.send_message(
            recipient_id,
            f"✅ Ответ администратора\n\n"
            f"{response_text}"
        )
        
        await message.answer(
            f"✅ Ответ отправлен пользователю @{recipient_username}"
        )
        
        await LogRepository.create_log(
            session, "proxy_response_sent", recipient_id, 
            admin_id=message.from_user.id,
            description=f"Response: {response_text}"
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при отправке ответа\n\n"
            f"Ошибка: {str(e)}"
        )

    await state.clear()
    await message.answer(
        "👨‍💼 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=get_admin_main_keyboard()
    )



@admin_router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Вернуться в главное меню администратора"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            "👨‍💼 Панель администратора\n\n"
            "Выберите действие:",
            reply_markup=get_admin_main_keyboard()
        )
    except Exception:
        pass
    await callback.answer()


@admin_router.callback_query(F.data == "accounts_all")
async def show_all_accounts(callback: CallbackQuery, session: AsyncSession):
    """Показать все аккаунты и отправить архив со всеми файлами"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    accounts = await AccountRepository.get_all_accounts(session)

    if not accounts:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_view_accounts")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text("📭 Аккаунты не найдены", reply_markup=keyboard)
        await callback.answer()
        return

    # Подготовить список существующих файлов из data/uploads
    from config import UPLOAD_DIR
    existing_files = []
    for acc in accounts:
        path = UPLOAD_DIR / str(acc.user_id) / acc.file_path
        if path.exists():
            existing_files.append((acc, path))

    # Создать архив со всеми файлами
    import tempfile, zipfile, os
    
    bot = Bot(token=BOT_TOKEN)
    tmp_zip = None
    
    try:
        # Создать временный ZIP-архив
        tmp = tempfile.NamedTemporaryFile(prefix="accounts_all_", suffix=".zip", delete=False)
        tmp_zip = tmp.name
        tmp.close()

        # Добавить все файлы в архив
        with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for acc, path in existing_files:
                arcname = f"account_{acc.id}_{path.name}"
                zf.write(str(path), arcname=arcname)

        # Отправить архив
        await callback.message.edit_text(f"📦 Отправляю архив со всеми {len(existing_files)} файлами...")
        await bot.send_document(callback.from_user.id, FSInputFile(tmp_zip))
        
        # Отправить итог
        await callback.message.answer(f"✅ Всего аккаунтов: {len(accounts)} (файлов архивировано: {len(existing_files)})")
    
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при создании архива: {str(e)}")
    
    finally:
        # Очистка временного файла
        if tmp_zip and os.path.exists(tmp_zip):
            try:
                os.remove(tmp_zip)
            except Exception:
                pass

    await callback.answer()


@admin_router.callback_query(F.data == "accounts_by_user")
async def accounts_by_user(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать список пользователей для выбора"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    users = await UserRepository.get_all_users(session)
    if not users:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_view_accounts")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text("👥 Пользователи не найдены", reply_markup=keyboard)
        await callback.answer()
        return

    # Построить inline-клавиатуру со списком пользователей
    kb_buttons = []
    for u in users:
        label = f"{u.username or u.tg_id} ({u.tg_id})"
        kb_buttons.append([InlineKeyboardButton(text=label, callback_data=f"accounts_user_{u.id}")])

    # добавить кнопку назад
    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text("👤 Выберите пользователя:", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("accounts_user_"))
async def accounts_user_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать аккаунты пользователя кнопками"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Некорректный пользователь.", show_alert=True)
        return

    # Получить все аккаунты пользователя
    accounts = await AccountRepository.get_accounts_by_user(session, user_id)
    
    if not accounts:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="accounts_by_user")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text(f"📭 Аккаунты не найдены для пользователя ID {user_id}", reply_markup=keyboard)
        await callback.answer()
        return

    # Построить кнопки с названиями и статусами аккаунтов
    kb_buttons = []
    for acc in accounts:
        # Определить статус: Проверен (sent=True, locked=False) - ✅; Заблокирован - 🔒; Не проверен - ❌
        if acc.sent and not acc.locked:
            status_emoji = "✅"
            status_text = "Проверен"
        elif acc.locked:
            status_emoji = "🔒"
            status_text = "Заблокирован"
        else:
            status_emoji = "❌"
            status_text = "Не проверен"
        
        # Извлечь только имя файла (без пути)
        filename = Path(acc.file_path).name
        button_text = f"{status_emoji} {filename} - {status_text}"
        kb_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"acc_edit_{acc.id}")])

    # Добавить кнопку назад
    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(
        f"👤 Аккаунты пользователя (ID {user_id}):\n\n"
        f"Всего: {len(accounts)}",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("acc_edit_"))
async def edit_account_status(callback: CallbackQuery, session: AsyncSession):
    """Показать детали аккаунта с возможностью изменения"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        account_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Некорректный аккаунт.", show_alert=True)
        return

    account = await AccountRepository.get_account_by_id(session, account_id)
    if not account:
        await callback.answer("❌ Аккаунт не найден.", show_alert=True)
        return

    message_text = format_account_info(account)

    # Построить кнопки для действий
    kb_buttons = []
    
    # Если не отправлен, добавить кнопку "Отправлено"
    if not account.sent:
        kb_buttons.append([InlineKeyboardButton(text="✅ Отправлено", callback_data=f"account_sent_{account.id}")])
    
    # Кнопки блокировки/разблокировки
    if not account.locked:
        kb_buttons.append([InlineKeyboardButton(text="🔒 Заблокировать", callback_data=f"account_lock_{account.id}")])
    else:
        kb_buttons.append([InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"account_unlock_{account.id}")])

    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"accounts_user_{account.user_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("acc_status_"))
async def set_account_status(callback: CallbackQuery, session: AsyncSession):
    """Установить статус аккаунта и уведомить пользователя"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        parts = callback.data.split("_")
        account_id = int(parts[2])
        status = parts[3]  # verified, locked, unverified
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    account = await AccountRepository.get_account_by_id(session, account_id)
    if not account:
        await callback.answer("❌ Аккаунт не найден.", show_alert=True)
        return

    # Обновить статус в зависимости от выбора
    if status == "locked":
        account.locked = True
        account.sent = True
        status_text = "Заблокирован 🔒"
    else:  # unverified
        account.sent = False
        account.locked = False
        status_text = "Не проверен ❌"

    await session.commit()

    # Отправить уведомление пользователю
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)
    user = await UserRepository.get_user_by_id(session, account.user_id)
    filename = Path(account.file_path).name
    
    try:
        await bot.send_message(
            user.tg_id,
            f"📋 Статус вашего аккаунта обновлен\n\n"
            f"📁 Аккаунт: {filename}\n"
            f"📊 Новый статус: {status_text}"
        )
    except Exception as e:
        await callback.message.answer(f"⚠️ Статус обновлен, но не удалось отправить уведомление пользователю: {str(e)}")

    await callback.message.edit_text(
        f"✅ Статус аккаунта {filename} изменен на: {status_text}\n\n"
        f"Пользователь уведомлен."
    )
    await callback.answer()


@admin_router.callback_query(F.data == "accounts_unsent")
async def show_unsent_accounts(callback: CallbackQuery, session: AsyncSession):
    """Показать список пользователей с неотправленными аккаунтами"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    accounts = await AccountRepository.get_unsent_accounts(session)

    if not accounts:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_view_accounts")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text("✅ Все аккаунты отправлены", reply_markup=keyboard)
        await callback.answer()
        return

    # Получить уникальных пользователей с неотправленными аккаунтами
    users_dict = {}
    for account in accounts:
        if account.user_id not in users_dict:
            user = await UserRepository.get_user_by_id(session, account.user_id)
            if user:
                users_dict[account.user_id] = user

    # Построить кнопки пользователей
    kb_buttons = []
    for user_id, user in users_dict.items():
        label = f"{user.username or user.tg_id}"
        kb_buttons.append([InlineKeyboardButton(text=label, callback_data=f"unsent_user_{user_id}")])

    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_view_accounts")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    
    await callback.message.edit_text(
        f"⏳ Неотправленные аккаунты\n\n"
        f"Всего аккаунтов: {len(accounts)}\n"
        f"Пользователей: {len(users_dict)}\n\n"
        f"Выберите пользователя:",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("unsent_user_"))
async def show_user_unsent_accounts(callback: CallbackQuery, session: AsyncSession):
    """Показать неотправленные аккаунты выбранного пользователя"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    # Получить все аккаунты пользователя
    accounts = await AccountRepository.get_accounts_by_user(session, user_id)
    # Отфильтровать только неотправленные
    unsent_accounts = [acc for acc in accounts if not acc.sent]

    if not unsent_accounts:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="accounts_unsent")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text(
            "✅ У этого пользователя нет неотправленных аккаунтов",
            reply_markup=keyboard
        )
        await callback.answer()
        return

    # Построить кнопки аккаунтов
    kb_buttons = []
    for account in unsent_accounts:
        status_locked = "🔒" if account.locked else "✅"
        label = f"{status_locked} #{account.id} | {account.month}"
        kb_buttons.append([InlineKeyboardButton(text=label, callback_data=f"unsent_account_{account.id}")])

    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="accounts_unsent")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    user = await UserRepository.get_user_by_id(session, user_id)
    await callback.message.edit_text(
        f"⏳ Неотправленные аккаунты @{user.username}\n\n"
        f"Выберите аккаунт:",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("unsent_account_"))
async def show_unsent_account_details(callback: CallbackQuery, session: AsyncSession):
    """Показать детали неотправленного аккаунта с кнопкой отправки"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        account_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    account = await AccountRepository.get_account_by_id(session, account_id)
    if not account:
        await callback.message.edit_text("❌ Аккаунт не найден")
        await callback.answer()
        return

    user = await UserRepository.get_user_by_id(session, account.user_id)
    message_text = format_account_info(account)
    message_text += f"\n\n👤 Пользователь: @{user.username}"

    # Построить кнопки действий
    kb_buttons = [
        [InlineKeyboardButton(text="✅ Отправлено", callback_data=f"account_sent_{account.id}")],
    ]

    if not account.locked:
        kb_buttons.append([InlineKeyboardButton(text="🔒 Заблокировать", callback_data=f"account_lock_{account.id}")])
    else:
        kb_buttons.append([InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"account_unlock_{account.id}")])

    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"unsent_user_{account.user_id}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("account_sent_"))
async def mark_account_sent(callback: CallbackQuery, session: AsyncSession):
    """Отметить аккаунт как отправленный"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        account_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    account = await AccountRepository.get_account_by_id(session, account_id)
    if not account:
        await callback.answer("❌ Аккаунт не найден.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, account.user_id)
    
    # Отметить как отправленный
    account.sent = True
    await session.commit()

    # Отправить уведомление пользователю
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)
    filename = Path(account.file_path).name
    
    try:
        await bot.send_message(
            user.tg_id,
            f"✅ Ваш аккаунт отправлен\n\n"
            f"📁 Файл: {filename}\n"
            f"📊 Статус: Отправлен"
        )
    except:
        pass

    kb_buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"unsent_user_{account.user_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    
    await callback.message.edit_text(
        f"✅ Аккаунт {filename} отмечен как отправленный\n\n"
        f"Пользователь @{user.username} уведомлен.",
        reply_markup=keyboard
    )
    
    await LogRepository.create_log(session, "account_marked_sent", account.user_id, admin_id=callback.from_user.id)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("account_lock_"))
async def lock_account(callback: CallbackQuery, session: AsyncSession):
    """Заблокировать аккаунт"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        account_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    account = await AccountRepository.get_account_by_id(session, account_id)
    if not account:
        await callback.answer("❌ Аккаунт не найден.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, account.user_id)
    
    # Заблокировать
    account.locked = True
    await session.commit()

    # Отправить уведомление пользователю
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)
    filename = Path(account.file_path).name
    
    try:
        await bot.send_message(
            user.tg_id,
            f"🔒 Ваш аккаунт заблокирован\n\n"
            f"📁 Файл: {filename}\n"
            f"📊 Статус: Заблокирован"
        )
    except:
        pass

    kb_buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"unsent_user_{account.user_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    
    await callback.message.edit_text(
        f"✅ Аккаунт {filename} заблокирован\n\n"
        f"Пользователь @{user.username} уведомлен.",
        reply_markup=keyboard
    )
    
    await LogRepository.create_log(session, "account_locked", account.user_id, admin_id=callback.from_user.id)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("account_unlock_"))
async def unlock_account(callback: CallbackQuery, session: AsyncSession):
    """Разблокировать аккаунт"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        account_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    account = await AccountRepository.get_account_by_id(session, account_id)
    if not account:
        await callback.answer("❌ Аккаунт не найден.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, account.user_id)
    
    # Разблокировать
    account.locked = False
    await session.commit()

    # Отправить уведомление пользователю
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)
    filename = Path(account.file_path).name
    
    try:
        await bot.send_message(
            user.tg_id,
            f"🔓 Ваш аккаунт разблокирован\n\n"
            f"📁 Файл: {filename}\n"
            f"📊 Статус: Разблокирован"
        )
    except:
        pass

    kb_buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"unsent_user_{account.user_id}")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    
    await callback.message.edit_text(
        f"✅ Аккаунт {filename} разблокирован\n\n"
        f"Пользователь @{user.username} уведомлен.",
        reply_markup=keyboard
    )
    
    await LogRepository.create_log(session, "account_unlocked", account.user_id, admin_id=callback.from_user.id)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("notify_") & ~F.data.startswith("notify_user_select_"))
async def handle_notification_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработчик выбора типа уведомления"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    notification_type = callback.data.replace("notify_", "")

    if notification_type == "custom":
        # Кастомное уведомление
        await callback.message.edit_text(
            "📝 Кастомное уведомление\n\n"
            "Введите текст уведомления:"
        )
        await state.set_state(AdminStates.waiting_for_custom_notification_text)
        await callback.answer()
        return

    if notification_type in ["salary", "call", "penalty"]:
        # Сохранить тип уведомления в состояние
        await state.update_data(notification_type=notification_type)
        
        # Для созвона запросить время и дату
        if notification_type == "call":
            await callback.message.edit_text(
                "📞 Назначить созвон\n\n"
                "Введите дату и время в формате: DD.MM.YYYY HH:MM\n"
                "Пример: 14.11.2025 15:30"
            )
            await state.set_state(AdminStates.waiting_for_call_datetime)
        else:
            # Спросить кому отправить для остальных типов
            kb_buttons = [
                [InlineKeyboardButton(text="👤 Конкретному пользователю", callback_data="notify_single")],
                [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="notify_all")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_send_notification")],
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
            await callback.message.edit_text(
                "👥 Кому отправить уведомление?",
                reply_markup=keyboard
            )
        await callback.answer()
        return
        
    elif notification_type in ["single", "all"]:
        await state.update_data(recipient_type=notification_type)

        if notification_type == "single":
            # Показать список пользователей
            users = await UserRepository.get_all_users(session)
            if not users:
                await callback.message.edit_text("👥 Пользователи не найдены")
                await callback.answer()
                return

            # Построить inline-клавиатуру со списком пользователей
            kb_buttons = []
            for user in users:
                if user.tg_id == callback.from_user.id:  # Пропустить текущего админа
                    continue
                label = f"@{user.username}" if user.username else f"ID: {user.tg_id}"
                kb_buttons.append([InlineKeyboardButton(text=label, callback_data=f"notify_user_select_{user.id}")])

            if not kb_buttons:
                await callback.message.edit_text("👥 Нет других пользователей")
                await callback.answer()
                return

            kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_send_notification")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

            await callback.message.edit_text(
                "👤 Выберите пользователя для отправки уведомления:",
                reply_markup=keyboard
            )
        else:  # all
            data = await state.get_data()
            notification_type = data.get("notification_type", "custom")
            
            if notification_type == "custom":
                text = data.get("custom_notification_text")
            else:
                call_datetime = data.get("call_datetime")
                text = get_notification_text(notification_type, call_datetime)
            
            kb_buttons = [
                [InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no")],
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
            
            await callback.message.edit_text(
                f"📢 Уведомление\n\n{text}\n\n"
                "Нажмите 'Да' для отправки всем пользователям или 'Нет' для отмены",
                reply_markup=keyboard
            )

    await callback.answer()


@admin_router.message(AdminStates.waiting_for_call_datetime)
async def get_call_datetime(message: Message, state: FSMContext):
    """Получить дату и время для созвона"""
    datetime_text = message.text.strip()
    
    try:
        call_datetime = datetime.strptime(datetime_text, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте DD.MM.YYYY HH:MM (например: 14.11.2025 15:30)")
        return
    
    await state.update_data(call_datetime=datetime_text)
    
    # Спросить кому отправить
    kb_buttons = [
        [InlineKeyboardButton(text="👤 Конкретному пользователю", callback_data="notify_single")],
        [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="notify_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_send_notification")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    
    await message.answer(
        "👥 Кому отправить уведомление?",
        reply_markup=keyboard
    )


@admin_router.message(AdminStates.waiting_for_custom_notification_text)
async def handle_custom_notification_text(message: Message, state: FSMContext):
    """Обработчик текста кастомного уведомления"""
    if not is_admin(message):
        await message.answer("❌ У вас нет доступа.")
        await state.clear()
        return

    custom_text = message.text.strip()
    if not custom_text:
        await message.answer("❌ Текст не введен. Пожалуйста, попробуйте еще раз.")
        return

    await state.update_data(custom_notification_text=custom_text, notification_type="custom")
    
    # Спросить кому отправить
    kb_buttons = [
        [InlineKeyboardButton(text="👤 Конкретному пользователю", callback_data="notify_single")],
        [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="notify_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_send_notification")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    
    await message.answer(
        f"📝 Ваше уведомление:\n\n{custom_text}\n\n"
        "Кому отправить?",
        reply_markup=keyboard
    )


@admin_router.callback_query(F.data.startswith("notify_user_select_"))
async def select_notification_user(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбрать пользователя для отправки уведомления из списка"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception as e:
        import logging
        logging.error(f"Error parsing user_id from {callback.data}: {e}")
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    data = await state.get_data()
    await state.update_data(recipient_id=user.tg_id)
    
    # Получить текст уведомления в зависимости от типа
    notification_type = data.get("notification_type", "custom")
    
    if notification_type == "custom":
        text = data.get("custom_notification_text", "Тестовое уведомление")
    else:
        call_datetime = data.get("call_datetime", "")
        text = get_notification_text(notification_type, call_datetime)

    if not text:
        text = "Уведомление"

    kb_buttons = [
        [InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    user_label = f"ID: {user.tg_id}"
    if user.username and user.username != "!":
        user_label = f"@{user.username}"
    
    message_text = f"📢 Уведомление для {user_label}\n\n{text}\n\nНажмите 'Да' для отправки или 'Нет' для отмены"
    
    try:
        await callback.message.edit_text(message_text, reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error editing message: {e}")
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)
        return
    
    await callback.answer()


@admin_router.callback_query(F.data == "confirm_yes")
async def send_notification(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Отправить уведомление"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    data = await state.get_data()
    recipient_type = data.get("recipient_type", "single")
    recipient_id = data.get("recipient_id")
    notification_type = data.get("notification_type", "custom")

    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)

    # Получить текст в зависимости от типа уведомления
    if notification_type == "custom":
        text = data.get("custom_notification_text", "Уведомление")
        log_action = "custom_notification_sent"
    else:
        call_datetime = data.get("call_datetime", "")
        text = get_notification_text(notification_type, call_datetime)
        log_action = f"notification_sent_{notification_type}"

    if recipient_type == "single":
        if not recipient_id:
            await callback.message.edit_text("❌ Ошибка: получатель не выбран")
            await callback.answer()
            return
        
        try:
            await bot.send_message(recipient_id, text)
            await callback.message.edit_text("✅ Уведомление отправлено")
            await LogRepository.create_log(
                session, log_action, 
                recipient_id, admin_id=callback.from_user.id
            )
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка при отправке\n\n{str(e)}")
    else:  # all
        users = await UserRepository.get_all_users(session)
        sent_count = 0
        for user in users:
            if user.access:  # Отправить только пользователям с доступом
                try:
                    await bot.send_message(user.tg_id, text)
                    sent_count += 1
                except:
                    pass

        await callback.message.edit_text(
            f"✅ Уведомление отправлено {sent_count} пользователям"
        )
        
        log_action_all = log_action.replace("_sent", "_sent_all")
        await LogRepository.create_log(
            session, log_action_all,
            admin_id=callback.from_user.id,
            description=f"Sent to {sent_count} users"
        )

    await state.clear()
    await callback.answer()


@admin_router.callback_query(F.data == "confirm_no")
async def cancel_notification(callback: CallbackQuery, state: FSMContext):
    """Отменить отправку уведомления"""
    await callback.message.edit_text("❌ Отменено")
    await state.clear()
    await callback.answer()


@admin_router.callback_query(F.data == "manage_allow_user")
async def manage_allow_user_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать список пользователей для разрешения доступа"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    users = await UserRepository.get_all_users(session)
    if not users:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text("👥 Нет пользователей", reply_markup=keyboard)
        await callback.answer()
        return

    # Построить кнопки пользователей без доступа
    kb_buttons = []
    for user in users:
        if not user.access:
            label = f"@{user.username}" if user.username else f"ID: {user.tg_id}"
            kb_buttons.append([InlineKeyboardButton(text=label, callback_data=f"user_allow_{user.id}")])

    if not kb_buttons:
        kb_buttons_empty = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons_empty)
        await callback.message.edit_text("✅ Все пользователи уже имеют доступ", reply_markup=keyboard)
        await callback.answer()
        return

    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text("✅ Выберите пользователя для разрешения доступа:", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "manage_deny_user")
async def manage_deny_user_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать список пользователей для запрещения доступа"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    users = await UserRepository.get_all_users(session)
    if not users:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text("👥 Нет пользователей", reply_markup=keyboard)
        await callback.answer()
        return

    # Построить кнопки пользователей с доступом
    kb_buttons = []
    for user in users:
        if user.access:
            label = f"@{user.username}" if user.username else f"ID: {user.tg_id}"
            kb_buttons.append([InlineKeyboardButton(text=label, callback_data=f"user_deny_{user.id}")])

    if not kb_buttons:
        kb_buttons_empty = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons_empty)
        await callback.message.edit_text("❌ Все пользователи уже без доступа", reply_markup=keyboard)
        await callback.answer()
        return

    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text("❌ Выберите пользователя для запрещения доступа:", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "manage_user_info")
async def manage_user_info_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать список пользователей для получения информации"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    users = await UserRepository.get_all_users(session)
    if not users:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text("👥 Нет пользователей", reply_markup=keyboard)
        await callback.answer()
        return

    # Построить кнопки всех пользователей
    kb_buttons = []
    for user in users:
        label = f"{user.username or user.tg_id}"
        kb_buttons.append([InlineKeyboardButton(text=label, callback_data=f"user_info_{user.id}")])

    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text("📋 Выберите пользователя для получения информации:", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "manage_list_users")
async def manage_list_users_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать список всех пользователей"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    users = await UserRepository.get_all_users(session)
    if not users:
        kb_buttons = [
            [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text("👥 Нет пользователей", reply_markup=keyboard)
        await callback.answer()
        return

    message_text = "👥 Список пользователей\n\n"
    for user in users[:30]:
        access_status = "✅" if user.access else "❌"
        message_text += (
            f"{access_status} {user.username or user.tg_id} (ID:{user.id})\n"
        )

    if len(users) > 30:
        message_text += f"\n... и еще {len(users) - 30} пользователей"

    kb_buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_users")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("user_allow_"))
async def handle_user_allow(callback: CallbackQuery, session: AsyncSession):
    """Разрешить доступ выбранному пользователю"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    user = await UserRepository.update_user_access(session, user_id, True)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"✅ Доступ разрешен\n\n"
        f"Пользователю @{user.username} разрешен доступ к боту."
    )

    # Отправить уведомление пользователю
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            user.tg_id,
            "✅ Вам разрешен доступ к боту\n\n"
            "Теперь вы можете использовать все функции."
        )
    except:
        pass

    await LogRepository.create_log(session, "user_access_allowed", user.id, admin_id=callback.from_user.id)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("user_deny_"))
async def handle_user_deny(callback: CallbackQuery, session: AsyncSession):
    """Запретить доступ выбранному пользователю"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    user = await UserRepository.update_user_access(session, user_id, False)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"❌ Доступ запрещен\n\n"
        f"Пользователю @{user.username} запрещен доступ к боту."
    )

    # Отправить уведомление пользователю
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            user.tg_id,
            "❌ Вам запрещен доступ к боту\n\n"
            "Свяжитесь с администратором для получения дополнительной информации."
        )
    except:
        pass

    await LogRepository.create_log(session, "user_access_denied", user.id, admin_id=callback.from_user.id)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("user_info_"))
async def handle_user_info(callback: CallbackQuery, session: AsyncSession):
    """Показать информацию о выбранном пользователе"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("Ошибка обработки.", show_alert=True)
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.")
        await callback.answer()
        return

    accounts = await AccountRepository.get_accounts_by_user(session, user_id)
    message_text = format_user_info(user)
    message_text += f"\n\n📊 Загруженных архивов: {len(accounts)}"

    await callback.message.edit_text(message_text)
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_user_manage_username)
async def handle_user_manage_username(message: Message, state: FSMContext, session: AsyncSession):
    """Обработать username для управления пользователем"""
    username = message.text.strip()
    
    # Поискать пользователя по username
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer(f"❌ Пользователь с username '{username}' не найден.")
        return

    data = await state.get_data()
    action = data.get("manage_action")

    if action == "allow":
        await UserRepository.update_user_access(session, user.id, True)
        await message.answer(
            f"✅ Доступ разрешен\n\n"
            f"Пользователю @{user.username} разрешен доступ к боту."
        )
        
        # Отправить уведомление пользователю
        bot = Bot(token=BOT_TOKEN)
        try:
            await bot.send_message(
                user.tg_id,
                "✅ Вам разрешен доступ к боту\n\n"
                "Теперь вы можете использовать все функции."
            )
        except:
            pass
        
        await LogRepository.create_log(session, "user_access_allowed", user.id, admin_id=message.from_user.id)
        
    elif action == "deny":
        await UserRepository.update_user_access(session, user.id, False)
        await message.answer(
            f"❌ Доступ запрещен\n\n"
            f"Пользователю @{user.username} запрещен доступ к боту."
        )
        
        # Отправить уведомление пользователю
        bot = Bot(token=BOT_TOKEN)
        try:
            await bot.send_message(
                user.tg_id,
                "❌ Вам запрещен доступ к боту\n\n"
                "Свяжитесь с администратором для получения дополнительной информации."
            )
        except:
            pass
        
        await LogRepository.create_log(session, "user_access_denied", user.id, admin_id=message.from_user.id)
        
    elif action == "info":
        accounts = await AccountRepository.get_accounts_by_user(session, user.id)
        message_text = format_user_info(user)
        message_text += f"\n\n📊 Загруженных архивов: {len(accounts)}"
        await message.answer(message_text)

    await state.clear()
    await message.answer("Выберите действие:", reply_markup=get_admin_main_keyboard())


@admin_router.callback_query(F.data == "admin_add_admin")
async def add_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Начать процесс добавления администратора"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    await callback.message.edit_text(
        "➕ Добавить администратора\n\n"
        "Введите username пользователя, которого нужно сделать администратором:"
    )
    await state.set_state(AdminStates.waiting_for_admin_username)
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_admin_username)
async def handle_admin_username(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик ввода username для добавления администратора"""
    username = message.text.strip().lstrip('@')
    
    # Найти пользователя по username
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer(
            f"❌ Пользователь @{username} не найден в базе данных.\n\n"
            "Убедитесь, что username введен правильно и пользователь уже зарегистрирован в боте."
        )
        await state.clear()
        await message.answer("Выберите действие:", reply_markup=get_admin_main_keyboard())
        return
    
    # Проверить, не администратор ли уже
    if user.tg_id in ADMIN_IDS:
        await message.answer(
            f"⚠️ Пользователь @{username} уже является администратором."
        )
        await state.clear()
        await message.answer("Выберите действие:", reply_markup=get_admin_main_keyboard())
        return
    
    # Показать информацию о пользователе и запросить подтверждение
    user_info = format_user_info(user)
    accounts = await AccountRepository.get_accounts_by_user(session, user.id)
    
    kb_buttons = [
        [
            InlineKeyboardButton(text="✅ Да, добавить админом", callback_data=f"confirm_add_admin_{user.id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    
    await message.answer(
        f"{user_info}\n\n"
        f"📊 Загруженных архивов: {len(accounts)}\n\n"
        f"⚠️ Вы уверены, что хотите сделать этого пользователя администратором?",
        reply_markup=keyboard
    )
    await state.clear()


@admin_router.callback_query(F.data.startswith("confirm_add_admin_"))
async def confirm_add_admin(callback: CallbackQuery, session: AsyncSession):
    """Подтвердить добавление администратора"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # Получить пользователя
    user = await session.get(User, user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Добавить в ADMIN_IDS (это требует изменения конфига, но мы можем отправить сообщение админу)
    await callback.message.edit_text(
        f"✅ Пользователь @{user.username} должен быть добавлен в ADMIN_IDS в config.py\n\n"
        f"Telegram ID: `{user.tg_id}`\n\n"
        f"Добавьте следующую строку в ADMIN_IDS в config.py:\n"
        f"`{user.tg_id},  # @{user.username}`\n\n"
        f"После этого перезагрузите бота."
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("approve_new_user_"))
async def approve_new_user(callback: CallbackQuery, session: AsyncSession):
    """Одобрить доступ для нового пользователя"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    user = await session.get(User, user_id)
    
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.")
        await callback.answer()
        return
    
    # Разрешить доступ
    await UserRepository.update_user_access(session, user.id, True)
    
    username_display = f"@{user.username}" if user.username else f"ID {user.tg_id}"
    
    # Уведомить пользователя
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            user.tg_id,
            "✅ Ваш доступ к боту разрешен!\n\n"
            "Теперь вы можете использовать все функции."
        )
    except:
        pass
    
    await callback.message.edit_text(
        f"✅ Доступ разрешен для {username_display}\n\n"
        f"ID: {user.tg_id}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")]
            ]
        )
    )
    await callback.answer()
    
    await LogRepository.create_log(session, "new_user_approved", user.id, admin_id=callback.from_user.id)


@admin_router.callback_query(F.data.startswith("deny_new_user_"))
async def deny_new_user(callback: CallbackQuery, session: AsyncSession):
    """Отказать в доступе для нового пользователя"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    user = await session.get(User, user_id)
    
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.")
        await callback.answer()
        return
    
    # Запретить доступ (уже по умолчанию access=False)
    await UserRepository.update_user_access(session, user.id, False)
    
    username_display = f"@{user.username}" if user.username else f"ID {user.tg_id}"
    
    # Уведомить пользователя
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            user.tg_id,
            "❌ Вам отказано в доступе к боту.\n\n"
            "Свяжитесь с администратором для получения дополнительной информации."
        )
    except:
        pass
    
    await callback.message.edit_text(
        f"❌ Доступ запрещен для {username_display}\n\n"
        f"ID: {user.tg_id}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="admin_back")]
            ]
        )
    )
    await callback.answer()
    
    await LogRepository.create_log(session, "new_user_denied", user.id, admin_id=callback.from_user.id)


