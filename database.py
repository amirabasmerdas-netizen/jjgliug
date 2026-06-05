from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime, timedelta
import config

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    user_type = Column(String, default='normal') # 'owner', 'normal', 'pro'
    pro_expiry = Column(DateTime, nullable=True)
    daily_views = Column(Integer, default=20)
    daily_reactions = Column(Integer, default=20)
    last_reset = Column(DateTime, default=datetime.utcnow)
    channel_id = Column(String, nullable=True)
    channel_verified = Column(Boolean, default=False)

class WorkerBot(Base):
    __tablename__ = 'worker_bots'
    id = Column(Integer, primary_key=True)
    bot_token = Column(String, unique=True)
    bot_username = Column(String)
    is_active = Column(Boolean, default=True)

engine = create_async_engine(config.DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_or_create_user(telegram_id: int) -> User:
    async with AsyncSessionLocal() as session:
        user = (await session.execute(User.__table__.select().where(User.telegram_id == telegram_id))).scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=telegram_id,
                user_type='normal',
                pro_expiry=datetime.utcnow() + timedelta(days=7) # دوره آزمایشی 7 روزه
            )
            session.add(user)
            await session.commit()
        return user

async def reset_daily_quotas():
    async with AsyncSessionLocal() as session:
        today = datetime.utcnow().date()
        # منطق ریست روزانه برای کاربران نرمال
        # (در یک سیستم واقعی بهتر است با Celery یا APScheduler انجام شود)
