from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.models import User, Account, Log


class UserRepository:
    """Репозиторий для работы с пользователями"""

    @staticmethod
    async def get_or_create_user(session: AsyncSession, tg_id: int, username: str = None):
        """Получить или создать пользователя"""
        from config import ADMIN_IDS
        
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Проверить, является ли пользователь администратором
            is_admin = tg_id in ADMIN_IDS
            user = User(tg_id=tg_id, username=username, access=is_admin)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

    @staticmethod
    async def get_user_by_tg_id(session: AsyncSession, tg_id: int):
        """Получить пользователя по Telegram ID"""
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int):
        """Получить пользователя по ID"""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user_access(session: AsyncSession, user_id: int, access: bool):
        """Обновить доступ пользователя"""
        user = await UserRepository.get_user_by_id(session, user_id)
        if user:
            user.access = access
            await session.commit()
            await session.refresh(user)
        return user

    @staticmethod
    async def update_user_wallet(session: AsyncSession, tg_id: int, wallet: str):
        """Обновить TRX кошелек пользователя"""
        user = await UserRepository.get_user_by_tg_id(session, tg_id)
        if user:
            user.trx_wallet = wallet
            await session.commit()
            await session.refresh(user)
        return user

    @staticmethod
    async def get_all_users(session: AsyncSession):
        """Получить всех пользователей"""
        stmt = select(User)
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def delete_user(session: AsyncSession, user_id: int):
        """Удалить пользователя"""
        user = await UserRepository.get_user_by_id(session, user_id)
        if user:
            await session.delete(user)
            await session.commit()
        return user


class AccountRepository:
    """Репозиторий для работы с аккаунтами"""

    @staticmethod
    async def create_account(session: AsyncSession, user_id: int, file_path: str, month: str):
        """Создать новый аккаунт"""
        account = Account(user_id=user_id, file_path=file_path, month=month)
        session.add(account)
        await session.commit()
        await session.refresh(account)
        return account

    @staticmethod
    async def get_account_by_id(session: AsyncSession, account_id: int):
        """Получить аккаунт по ID"""
        stmt = select(Account).where(Account.id == account_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_accounts_by_user(session: AsyncSession, user_id: int):
        """Получить все аккаунты пользователя"""
        stmt = select(Account).where(Account.user_id == user_id).order_by(Account.date_created.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_accounts_by_month(session: AsyncSession, month: str):
        """Получить все аккаунты за определенный месяц"""
        stmt = select(Account).where(Account.month == month).order_by(Account.date_created.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_all_accounts(session: AsyncSession):
        """Получить все аккаунты"""
        stmt = select(Account).order_by(Account.date_created.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_account_sent_status(session: AsyncSession, account_id: int, sent: bool):
        """Обновить статус отправки аккаунта"""
        account = await AccountRepository.get_account_by_id(session, account_id)
        if account:
            account.sent = sent
            await session.commit()
            await session.refresh(account)
        return account

    @staticmethod
    async def update_account_lock_status(session: AsyncSession, account_id: int, locked: bool):
        """Обновить статус блокировки аккаунта"""
        account = await AccountRepository.get_account_by_id(session, account_id)
        if account:
            account.locked = locked
            await session.commit()
            await session.refresh(account)
        return account

    @staticmethod
    async def get_unsent_accounts(session: AsyncSession):
        """Получить все неотправленные аккаунты"""
        stmt = select(Account).where(Account.sent == False).order_by(Account.date_created.desc())
        result = await session.execute(stmt)
        return result.scalars().all()


class LogRepository:
    """Репозиторий для работы с логами"""

    @staticmethod
    async def create_log(session: AsyncSession, action_type: str, user_id: int = None,
                        admin_id: int = None, description: str = None):
        """Создать новый лог"""
        log = Log(action_type=action_type, user_id=user_id, admin_id=admin_id, description=description)
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log

    @staticmethod
    async def get_logs(session: AsyncSession, limit: int = 100):
        """Получить последние логи"""
        stmt = select(Log).order_by(Log.timestamp.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()
