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
    get_account_actions_keyboard, get_confirm_keyboard
)
from app.utils.helpers import (
    get_current_month, format_account_info, format_user_info,
    get_notification_text
)
from config import ADMIN_IDS

admin_router = Router()


class AdminStates(StatesGroup):
    """Состояния для администратора"""
    waiting_for_month = State()
    waiting_for_notification_text = State()
    waiting_for_user_id = State()
    waiting_for_notification_recipient = State()
    waiting_for_user_id_manage = State()
    waiting_for_access_decision = State()


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


@admin_router.message(F.text == "📋 Просмотр аккаунтов")
async def view_accounts_menu(message: Message, session: AsyncSession):
    """Меню просмотра аккаунтов"""
    if not is_admin(message):
        await message.answer("❌ Доступ запрещен.")
        return

    await message.answer(
        "📋 Просмотр аккаунтов\n\n"
        "Выберите фильтр:",
        reply_markup=get_accounts_view_keyboard(),
        parse_mode="Markdown"
    )


@admin_router.callback_query(F.data == "accounts_all")
async def show_all_accounts(callback: CallbackQuery, session: AsyncSession):
    """Показать все аккаунты"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    accounts = await AccountRepository.get_all_accounts(session)

    if not accounts:
        await callback.message.edit_text("📭 Аккаунты не найдены", parse_mode="Markdown")
        return

    # Отправить по 5 аккаунтов в одном сообщении
    message_text = "📋 Все аккаунты\n\n"
    message_text += f"Всего: {len(accounts)}\n\n"

    for account in accounts[:10]:
        user = await UserRepository.get_user_by_id(session, account.user_id)
        status_sent = "✅" if account.sent else "❌"
        status_locked = "🔒" if account.locked else "🔓"
        message_text += (
            f"{status_sent} {status_locked} "
            f"ID:{account.id} | User:{user.username or account.user_id} | "
            f"{account.month} | {account.date_created.strftime('%d.%m %H:%M')}\n"
        )

    if len(accounts) > 10:
        message_text += f"\n... и еще {len(accounts) - 10} аккаунтов"

    await callback.message.edit_text(message_text, parse_mode="Markdown")
    await callback.answer()


@admin_router.callback_query(F.data == "accounts_by_month")
async def accounts_by_month_menu(callback: CallbackQuery, state: FSMContext):
    """Меню выбора месяца"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    await callback.message.edit_text(
        "📅 Выберите месяц\n\n"
        "Введите месяц в формате YYYY-MM (например: 2024-11)",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_month)
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_month)
async def show_accounts_by_month(message: Message, state: FSMContext, session: AsyncSession):
    """Показать аккаунты за месяц"""
    month = message.text.strip()

    # Проверить формат
    if len(month) != 7 or month[4] != '-':
        await message.answer(
            "❌ Неверный формат\n\n"
            "Используйте формат: YYYY-MM (например: 2024-11)",
            parse_mode="Markdown"
        )
        return

    accounts = await AccountRepository.get_accounts_by_month(session, month)

    if not accounts:
        await message.answer(
            f"📭 Аккаунты за {month} не найдены",
            parse_mode="Markdown"
        )
    else:
        message_text = f"📋 Аккаунты за {month}\n\n"
        message_text += f"Всего: {len(accounts)}\n\n"

        for account in accounts[:20]:
            user = await UserRepository.get_user_by_id(session, account.user_id)
            status_sent = "✅" if account.sent else "❌"
            status_locked = "🔒" if account.locked else "🔓"
            message_text += (
                f"{status_sent} {status_locked} "
                f"ID:{account.id} | @{user.username or 'unknown'}\n"
            )

        if len(accounts) > 20:
            message_text += f"\n... и еще {len(accounts) - 20} аккаунтов"

        await message.answer(message_text, parse_mode="Markdown")

    await state.clear()
    await message.answer(
        "Выберите действие:",
        reply_markup=get_admin_main_keyboard()
    )


@admin_router.callback_query(F.data == "accounts_unsent")
async def show_unsent_accounts(callback: CallbackQuery, session: AsyncSession):
    """Показать неотправленные аккаунты"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    accounts = await AccountRepository.get_unsent_accounts(session)

    if not accounts:
        await callback.message.edit_text(
            "✅ Все аккаунты отправлены",
            parse_mode="Markdown"
        )
        return

    message_text = "⏳ Неотправленные аккаунты\n\n"
    message_text += f"Всего: {len(accounts)}\n\n"

    for account in accounts[:15]:
        user = await UserRepository.get_user_by_id(session, account.user_id)
        status_locked = "🔒" if account.locked else "🔓"
        message_text += (
            f"{status_locked} ID:{account.id} | @{user.username or 'unknown'} | "
            f"{account.month}\n"
        )

    if len(accounts) > 15:
        message_text += f"\n... и еще {len(accounts) - 15} аккаунтов"

    await callback.message.edit_text(message_text, parse_mode="Markdown")
    await callback.answer()


@admin_router.message(F.text == "👥 Управление пользователями")
async def manage_users_menu(message: Message, session: AsyncSession):
    """Меню управления пользователями"""
    if not is_admin(message):
        await message.answer("❌ Доступ запрещен.")
        return

    users = await UserRepository.get_all_users(session)
    allowed_count = sum(1 for u in users if u.access)
    denied_count = len(users) - allowed_count

    message_text = (
        f"👥 Управление пользователями\n\n"
        f"Всего пользователей: {len(users)}\n"
        f"✅ Доступ разрешен: {allowed_count}\n"
        f"❌ Доступ запрещен: {denied_count}\n\n"
        f"/allow_user [ID] - разрешить доступ\n"
        f"/deny_user [ID] - запретить доступ\n"
        f"/user_info [ID] - информация о пользователе\n"
        f"/list_users - список всех пользователей"
    )

    await message.answer(message_text, parse_mode="Markdown")


@admin_router.message(Command("list_users"))
async def list_users(message: Message, session: AsyncSession):
    """Список всех пользователей"""
    if not is_admin(message):
        await message.answer("❌ Доступ запрещен.")
        return

    users = await UserRepository.get_all_users(session)

    if not users:
        await message.answer("👥 Нет пользователей", parse_mode="Markdown")
        return

    message_text = "👥 Список пользователей\n\n"
    for user in users[:30]:
        access_status = "✅" if user.access else "❌"
        message_text += (
            f"{access_status} ID:{user.id} | TG:{user.tg_id} | @{user.username or 'unknown'}\n"
        )

    if len(users) > 30:
        message_text += f"\n... и еще {len(users) - 30} пользователей"

    await message.answer(message_text, parse_mode="Markdown")


@admin_router.message(Command("user_info"))
async def user_info(message: Message, session: AsyncSession):
    """Информация о пользователе"""
    if not is_admin(message):
        await message.answer("❌ Доступ запрещен.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /user_info [USER_ID]\n\n"
            "Пример: /user_info 123",
            parse_mode="Markdown"
        )
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя.", parse_mode="Markdown")
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await message.answer("❌ Пользователь не найден.", parse_mode="Markdown")
        return

    accounts = await AccountRepository.get_accounts_by_user(session, user_id)
    message_text = format_user_info(user)
    message_text += f"\n\n📊 Загруженных архивов: {len(accounts)}"

    await message.answer(message_text, parse_mode="Markdown")


@admin_router.message(Command("allow_user"))
async def allow_user(message: Message, session: AsyncSession):
    """Разрешить доступ пользователю"""
    if not is_admin(message):
        await message.answer("❌ Доступ запрещен.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /allow_user [USER_ID]\n\n"
            "Пример: /allow_user 123",
            parse_mode="Markdown"
        )
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя.", parse_mode="Markdown")
        return

    user = await UserRepository.update_user_access(session, user_id, True)
    if not user:
        await message.answer("❌ Пользователь не найден.", parse_mode="Markdown")
        return

    await message.answer(
        f"✅ Доступ разрешен\n\n"
        f"Пользователю @{user.username or user.tg_id} разрешен доступ к боту.",
        parse_mode="Markdown"
    )

    # Отправить уведомление пользователю
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            user.tg_id,
            "✅ Вам разрешен доступ к боту\n\n"
            "Теперь вы можете использовать все функции.",
            parse_mode="Markdown"
        )
    except:
        pass

    await LogRepository.create_log(session, "user_access_allowed", user_id, admin_id=message.from_user.id)


@admin_router.message(Command("deny_user"))
async def deny_user(message: Message, session: AsyncSession):
    """Запретить доступ пользователю"""
    if not is_admin(message):
        await message.answer("❌ Доступ запрещен.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /deny_user [USER_ID]\n\n"
            "Пример: /deny_user 123",
            parse_mode="Markdown"
        )
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя.", parse_mode="Markdown")
        return

    user = await UserRepository.update_user_access(session, user_id, False)
    if not user:
        await message.answer("❌ Пользователь не найден.", parse_mode="Markdown")
        return

    await message.answer(
        f"❌ Доступ запрещен\n\n"
        f"Пользователю @{user.username or user.tg_id} запрещен доступ к боту.",
        parse_mode="Markdown"
    )

    # Отправить уведомление пользователю
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            user.tg_id,
            "❌ Вам запрещен доступ к боту\n\n"
            "Свяжитесь с администратором для получения дополнительной информации.",
            parse_mode="Markdown"
        )
    except:
        pass

    await LogRepository.create_log(session, "user_access_denied", user_id, admin_id=message.from_user.id)


@admin_router.message(F.text == "📢 Отправить уведомление")
async def send_notification_menu(message: Message):
    """Меню отправки уведомления"""
    if not is_admin(message):
        await message.answer("❌ Доступ запрещен.")
        return

    await message.answer(
        "📢 Отправить уведомление\n\n"
        "Выберите тип уведомления:",
        reply_markup=get_notification_type_keyboard(),
        parse_mode="Markdown"
    )


@admin_router.callback_query(F.data.startswith("notify_"))
async def handle_notification_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора типа уведомления"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    notification_type = callback.data.replace("notify_", "")

    if notification_type in ["salary", "call", "penalty"]:
        # Сохранить тип уведомления в состояние
        await state.update_data(notification_type=notification_type)
        
        # Спросить кому отправить
        await callback.message.edit_text(
            "👥 Кому отправить уведомление?",
            reply_markup=get_notification_recipient_keyboard(),
            parse_mode="Markdown"
        )
    elif notification_type in ["single", "all"]:
        data = await state.get_data()
        await state.update_data(recipient_type=notification_type)

        if notification_type == "single":
            await callback.message.edit_text(
                "👤 Введите ID пользователя\n\n"
                "Пример: 123456789",
                parse_mode="Markdown"
            )
            await state.set_state(AdminStates.waiting_for_user_id)
        else:
            # Отправить всем
            notification_type = data.get("notification_type")
            text = get_notification_text(notification_type)
            
            await callback.message.edit_text(
                f"📢 Уведомление\n\n{text}\n\n"
                "Нажмите 'Да' для отправки всем пользователям или 'Нет' для отмены",
                reply_markup=get_confirm_keyboard(),
                parse_mode="Markdown"
            )

    await callback.answer()


@admin_router.message(AdminStates.waiting_for_user_id)
async def get_notification_recipient_id(message: Message, state: FSMContext, session: AsyncSession):
    """Получить ID пользователя для уведомления"""
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID.", parse_mode="Markdown")
        return

    user = await UserRepository.get_user_by_id(session, user_id)
    if not user:
        await message.answer("❌ Пользователь не найден.", parse_mode="Markdown")
        return

    data = await state.get_data()
    notification_type = data.get("notification_type")
    text = get_notification_text(notification_type)

    await state.update_data(recipient_id=user_id)

    await message.answer(
        f"📢 Уведомление для @{user.username or user.tg_id}\n\n"
        f"{text}\n\n"
        f"Нажмите 'Да' для отправки или 'Нет' для отмены",
        reply_markup=get_confirm_keyboard(),
        parse_mode="Markdown"
    )


@admin_router.callback_query(F.data == "confirm_yes")
async def send_notification(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Отправить уведомление"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    data = await state.get_data()
    notification_type = data.get("notification_type")
    recipient_type = data.get("recipient_type", "single")
    recipient_id = data.get("recipient_id")

    text = get_notification_text(notification_type)

    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)

    if recipient_type == "single":
        try:
            await bot.send_message(recipient_id, text, parse_mode="Markdown")
            await callback.message.edit_text(
                f"✅ Уведомление отправлено",
                parse_mode="Markdown"
            )
            await LogRepository.create_log(
                session, f"notification_sent_{notification_type}", 
                recipient_id, admin_id=callback.from_user.id
            )
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Ошибка при отправке\n\n{str(e)}",
                parse_mode="Markdown"
            )
    else:  # all
        users = await UserRepository.get_all_users(session)
        sent_count = 0
        for user in users:
            if user.access:  # Отправить только пользователям с доступом
                try:
                    await bot.send_message(user.tg_id, text, parse_mode="Markdown")
                    sent_count += 1
                except:
                    pass

        await callback.message.edit_text(
            f"✅ Уведомление отправлено {sent_count} пользователям",
            parse_mode="Markdown"
        )
        await LogRepository.create_log(
            session, f"notification_sent_all_{notification_type}",
            admin_id=callback.from_user.id,
            description=f"Sent to {sent_count} users"
        )

    await state.clear()
    await callback.answer()


@admin_router.callback_query(F.data == "confirm_no")
async def cancel_notification(callback: CallbackQuery, state: FSMContext):
    """Отменить отправку уведомления"""
    await callback.message.edit_text(
        "❌ Отменено",
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer()


@admin_router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Вернуться в главное меню админа"""
    if not is_admin(callback):
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    await callback.answer()
    await callback.message.delete()


@admin_router.message(F.text == "🔐 Управление доступами")
async def manage_access_menu(message: Message, session: AsyncSession):
    """Меню управления доступами"""
    if not is_admin(message):
        await message.answer("❌ Доступ запрещен.")
        return

    await message.answer(
        "🔐 Управление доступами\n\n"
        "Доступные команды:\n\n"
        "/allow_user [ID] - разрешить доступ\n"
        "/deny_user [ID] - запретить доступ\n"
        "/list_users - список пользователей"
    )
