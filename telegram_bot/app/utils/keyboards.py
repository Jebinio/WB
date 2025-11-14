from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ============ ПОЛЬЗОВАТЕЛЬСКИЕ КЛАВИАТУРЫ ============

def get_user_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню пользователя"""
    buttons = [
        [InlineKeyboardButton(text="📤 Отправить аккаунт", callback_data="user_send_account")],
        [InlineKeyboardButton(text="🌐 Запросить прокси", callback_data="user_request_proxy")],
        [InlineKeyboardButton(text="📱 Запросить номера", callback_data="user_request_numbers")],
        [InlineKeyboardButton(text="💳 Прикрепить TRX-кошелек", callback_data="user_attach_wallet")],
        [InlineKeyboardButton(text="🕒 Открыть смену", callback_data="user_open_shift")],
        [InlineKeyboardButton(text="🔒 Закрыть смену", callback_data="user_close_shift")],
    ]
    
    # Добавить кнопку админа если пользователь админ
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👨‍💼 Админ панель", callback_data="user_to_admin_panel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


# ============ АДМИНСКИЕ КЛАВИАТУРЫ ============

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню администратора"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Просмотр аккаунтов", callback_data="admin_view_accounts")],
            [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_manage_users")],
            [InlineKeyboardButton(text="📢 Отправить уведомление", callback_data="admin_send_notification")],
            [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin")],
        ]
    )
    return keyboard


def get_accounts_view_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для просмотра аккаунтов"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 По пользователю", callback_data="accounts_by_user")],
            [InlineKeyboardButton(text="📊 Все аккаунты", callback_data="accounts_all")],
            [InlineKeyboardButton(text="⏳ Неотправленные", callback_data="accounts_unsent")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_view_accounts")],
        ]
    )
    return keyboard


def get_notification_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа уведомления"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Зарплата выдана", callback_data="notify_salary")],
            [InlineKeyboardButton(text="📞 Назначен созвон", callback_data="notify_call")],
            [InlineKeyboardButton(text="⚠️ Назначен штраф", callback_data="notify_penalty")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_send_notification")],
        ]
    )
    return keyboard


def get_notification_recipient_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора получателя уведомления"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Конкретному пользователю", callback_data="notify_single")],
            [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="notify_all")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_send_notification")],
        ]
    )
    return keyboard


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no"),
            ]
        ]
    )
    return keyboard


def get_account_actions_keyboard(account_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для управления аккаунтом"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправлено", callback_data=f"account_sent_{account_id}")],
            [InlineKeyboardButton(text="❌ Не отправлено", callback_data=f"account_unsent_{account_id}")],
            [InlineKeyboardButton(text="🔒 Заблокировать", callback_data=f"account_lock_{account_id}")],
            [InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"account_unlock_{account_id}")],
        ]
    )
    return keyboard


def get_new_user_approval_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для одобрения/отказа новому пользователю"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Разрешить", callback_data=f"approve_new_user_{user_id}"),
                InlineKeyboardButton(text="❌ Запретить", callback_data=f"deny_new_user_{user_id}")
            ]
        ]
    )
    return keyboard


def get_user_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления пользователями"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разрешить доступ", callback_data="manage_allow_user")],
            [InlineKeyboardButton(text="❌ Запретить доступ", callback_data="manage_deny_user")],
            [InlineKeyboardButton(text="📋 Информация о пользователе", callback_data="manage_user_info")],
            [InlineKeyboardButton(text="👥 Список всех пользователей", callback_data="manage_list_users")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
        ]
    )
    return keyboard
