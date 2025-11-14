from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ============ ПОЛЬЗОВАТЕЛЬСКИЕ КЛАВИАТУРЫ ============

def get_user_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню пользователя"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📤 Отправить аккаунт")],
            [KeyboardButton(text="🌐 Запросить прокси")],
            [KeyboardButton(text="📱 Запросить номера")],
            [KeyboardButton(text="💳 Прикрепить TRX-кошелек")],
        ],
        resize_keyboard=True
    )
    return keyboard


# ============ АДМИНСКИЕ КЛАВИАТУРЫ ============

def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню администратора"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Просмотр аккаунтов")],
            [KeyboardButton(text="👥 Управление пользователями")],
            [KeyboardButton(text="📢 Отправить уведомление")],
            [KeyboardButton(text="🔐 Управление доступами")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_accounts_view_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для просмотра аккаунтов"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 По месяцам", callback_data="accounts_by_month")],
            [InlineKeyboardButton(text="📊 Все аккаунты", callback_data="accounts_all")],
            [InlineKeyboardButton(text="⏳ Неотправленные", callback_data="accounts_unsent")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
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
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
        ]
    )
    return keyboard


def get_notification_recipient_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора получателя уведомления"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Конкретному пользователю", callback_data="notify_single")],
            [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="notify_all")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
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
