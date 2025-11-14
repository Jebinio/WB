from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    trx_wallet = Column(String(255), nullable=True)
    access = Column(Boolean, default=False)  # Доступ по умолчанию запрещен
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.tg_id} ({self.username})>"


class Account(Base):
    """Модель аккаунта"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    month = Column(String(7), nullable=False)  # YYYY-MM формат
    file_path = Column(String(512), nullable=False)
    sent = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    date_created = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Account {self.id} (user_id={self.user_id}, month={self.month})>"


class Log(Base):
    """Модель логирования"""
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    action_type = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Log {self.action_type} at {self.timestamp}>"


# Инициализация движка БД и сессии
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Добавить администраторов в БД с полным доступом
    from config import ADMIN_IDS
    async with AsyncSessionLocal() as session:
        for admin_id in ADMIN_IDS:
            # Проверить, существует ли администратор
            existing_admin = await session.execute(
                select(User).where(User.tg_id == admin_id)
            )
            admin = existing_admin.scalars().first()
            
            if not admin:
                # Создать администратора с доступом
                admin = User(
                    tg_id=admin_id,
                    username=f"admin_{admin_id}",
                    access=True  # Администраторы имеют доступ по умолчанию
                )
                session.add(admin)
        
        await session.commit()


async def get_db():
    """Получить сессию БД"""
    async with AsyncSessionLocal() as session:
        yield session
