# services/quota.py
from datetime import datetime, timedelta
import database as db
from sqlalchemy import update

async def check_and_decrement_quota(user: db.User, action: str) -> tuple[bool, str]:
    now = datetime.utcnow()
    if now.date() > user.last_reset.date():
        # ریست سهمیه
        if user.user_type == 'normal':
            user.daily_views = 20
            user.daily_reactions = 20
        user.last_reset = now
        await db.engine.execute(update(db.User).where(db.User.telegram_id == user.telegram_id).values(
            daily_views=user.daily_views, daily_reactions=user.daily_reactions, last_reset=now
        ))

    if user.user_type == 'normal':
        if action == 'view' and user.daily_views <= 0:
            return False, "سهمیه بازدید روزانه شما به پایان رسیده است."
        if action == 'reaction' and user.daily_reactions <= 0:
            return False, "سهمیه ری‌اکشن روزانه شما به پایان رسیده است."
    
    # بررسی انقضای دوره آزمایشی
    if user.user_type == 'normal' and user.pro_expiry < now:
        return False, "دوره آزمایشی رایگان شما به پایان رسیده است. لطفاً اشتراک پرو تهیه کنید."

    return True, "مجاز"

# services/channel.py
import asyncio
from aiogram import Bot

async def is_bot_admin_in_channel(bot: Bot, channel_id: str) -> bool:
    try:
        # حذف @ از ابتدای آیدی اگر وجود دارد
        clean_channel_id = channel_id.replace('@', '')
        member = await bot.get_chat_member(chat_id=clean_channel_id, user_id=bot.id)
        return member.status in ['administrator', 'creator']
    except Exception:
        return False
