import os
from datetime import datetime
from pathlib import Path
from config import UPLOAD_DIR


def get_current_month() -> str:
    """Получить текущий месяц в формате YYYY-MM"""
    return datetime.utcnow().strftime("%Y-%m")


def get_user_upload_dir(user_id: int) -> Path:
    """Получить директорию для загрузки файлов пользователя"""
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def save_uploaded_file(file_path: str, user_id: int, filename: str) -> str:
    """Сохранить загруженный файл и вернуть путь к нему"""
    user_dir = get_user_upload_dir(user_id)
    new_file_path = user_dir / filename
    return str(new_file_path)


def format_account_info(account) -> str:
    """Форматировать информацию об аккаунте"""
    status_sent = "✅ Отправлен" if account.sent else "❌ Не отправлен"
    status_locked = "🔒 Заблокирован" if account.locked else "🔓 Разблокирован"
    
    info = (
        f"📁 Аккаунт #{account.id}\n"
        f"👤 ID пользователя: {account.user_id}\n"
        f"📅 Месяц: {account.month}\n"
        f"📄 Файл: {Path(account.file_path).name}\n"
        f"📍 Статус отправки: {status_sent}\n"
        f"🔐 Статус блокировки: {status_locked}\n"
        f"⏰ Загружено: {account.date_created.strftime('%d.%m.%Y %H:%M:%S')}"
    )
    return info


def format_user_info(user) -> str:
    """Форматировать информацию о пользователе"""
    access_status = "✅ Доступ разрешен" if user.access else "❌ Доступ запрещен"
    wallet = user.trx_wallet or "Не установлен"
    
    info = (
        f"👤 Пользователь #{user.id}\n"
        f"🆔 Telegram ID: {user.tg_id}\n"
        f"📝 Username: {user.username or 'Не указан'}\n"
        f"💳 TRX кошелек: {wallet}\n"
        f"🔑 {access_status}\n"
        f"⏰ Дата создания: {user.created_at.strftime('%d.%m.%Y %H:%M:%S')}"
    )
    return info


def escape_markdown(text: str) -> str:
    """Экранировать спецсимволы для markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def get_notification_text(notification_type: str, call_datetime: str = None) -> str:
    """Получить текст уведомления по типу"""
    if notification_type == "call" and call_datetime:
        return f"📞 Назначен созвон\n\nДата и время: {call_datetime}"
    
    notifications = {
        "salary": "💰 Вам выплачена зарплата\n\nПроверьте ваш TRX кошелек для получения средств.",
        "call": "📞 Назначен созвон\n\nПожалуйста, подготовьтесь к встрече.",
        "penalty": "⚠️ Вам назначен штраф\n\nПодробности уточнены в личном сообщении.",
    }
    return notifications.get(notification_type, "📢 Новое уведомление")
