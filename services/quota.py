from datetime import datetime, timedelta
import database as db
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

async def check_and_decrement_quota(telegram_id: int, action: str) -> tuple[bool, str]:
    """
    بررسی سهمیه کاربر. این تابع تمام عملیات دیتابیس را در یک Session واحد انجام می‌دهد
    تا از خطاهای DetachedInstanceError جلوگیری شود.
    """
    now = datetime.utcnow()
    
    try:
        async with db.AsyncSessionLocal() as session:
            # دریافت کاربر از دیتابیس
            result = await session.execute(select(db.User).where(db.User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "کاربر یافت نشد. لطفاً /start را ارسال کنید."
            
            # 🔥 ریست روزانه سهمیه (همه چیز در یک Session)
            if user.last_reset is None or now.date() > user.last_reset.date():
                if user.user_type == 'normal':
                    user.daily_views = 20
                    user.daily_reactions = 20
                user.last_reset = now
                await session.commit()
                logger.info(f"Quota reset for user {telegram_id}")
            
            # بررسی محدودیت‌های کاربر عادی
            if user.user_type == 'normal':
                if action == 'view' and user.daily_views <= 0:
                    return False, "⚠️ سهمیه بازدید روزانه شما (20 عدد) به پایان رسیده است."
                if action == 'reaction' and user.daily_reactions <= 0:
                    return False, "⚠️ سهمیه ری‌اکشن روزانه شما (20 عدد) به پایان رسیده است."
            
            # بررسی انقضای دوره آزمایشی
            if user.user_type == 'normal' and user.pro_expiry and user.pro_expiry < now:
                return False, "⏰ دوره آزمایشی رایگان شما به پایان رسیده است. لطفاً اشتراک پرو تهیه کنید."
            
            return True, "مجاز"
            
    except Exception as e:
        logger.error(f"Error in check_and_decrement_quota: {e}")
        return False, "خطایی در بررسی سهمیه رخ داد. لطفاً دوباره تلاش کنید."
