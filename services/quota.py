from datetime import datetime, timedelta
import database as db
from sqlalchemy import update

async def check_and_decrement_quota(user: db.User, action: str) -> tuple[bool, str]:
    now = datetime.utcnow()
    
    # اگر last_reset None بود (کاربران قدیمی یا باگ دیتابیس)، مقداردهی کنیم
    if user.last_reset is None:
        user.last_reset = now - timedelta(days=1)

    if now.date() > user.last_reset.date():
        if user.user_type == 'normal':
            user.daily_views = 20
            user.daily_reactions = 20
        user.last_reset = now
        
        # 🔥 اصلاح: استفاده از session به جای engine.execute که در SQLAlchemy 2.0 حذف شده
        async with db.AsyncSessionLocal() as session:
            await session.execute(
                update(db.User).where(db.User.telegram_id == user.telegram_id).values(
                    daily_views=user.daily_views, 
                    daily_reactions=user.daily_reactions, 
                    last_reset=now
                )
            )
            await session.commit()

    if user.user_type == 'normal':
        if action == 'view' and user.daily_views <= 0:
            return False, "سهمیه بازدید روزانه شما به پایان رسیده است."
        if action == 'reaction' and user.daily_reactions <= 0:
            return False, "سهمیه ری‌اکشن روزانه شما به پایان رسیده است."
    
    if user.user_type == 'normal' and user.pro_expiry and user.pro_expiry < now:
        return False, "دوره آزمایشی رایگان شما به پایان رسیده است. لطفاً اشتراک پرو تهیه کنید."

    return True, "مجاز"
