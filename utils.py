from __future__ import annotations
from database import SessionLocal, User
from datetime import datetime, timedelta
from telegram import Bot

def get_or_create_user(telegram_id: int) -> User:
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, user_type="normal")
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

def check_and_reset_limits(user: User):
    today = datetime.utcnow().date()
    if user.last_reset_date.date() < today:
        user.daily_views = 0
        user.daily_reactions = 0
        user.last_reset_date = datetime.utcnow()
        db = SessionLocal()
        db.merge(user)
        db.commit()
        db.close()

def is_trial_expired(user: User) -> bool:
    if user.user_type == "pro":
        if user.pro_expiry and datetime.utcnow() > user.pro_expiry:
            user.user_type = "normal"
            db = SessionLocal()
            db.merge(user)
            db.commit()
            db.close()
            return True
        return False
    
    if user.user_type == "normal":
        trial_end = user.created_at + timedelta(days=7)
        return datetime.utcnow() > trial_end
    return False

def check_permission(user: User, action: str) -> tuple[bool, str]:
    check_and_reset_limits(user)
    
    if is_trial_expired(user):
        return False, "دوره آزمایشی رایگان شما به پایان رسیده است. لطفاً اشتراک پرو تهیه کنید."
    
    if user.user_type == "normal":
        if action == "view" and user.daily_views >= 20:
            return False, "سقف مجاز ویو روزانه شما (۲۰ عدد) به پایان رسیده است."
        if action == "reaction" and user.daily_reactions >= 20:
            return False, "سقف مجاز ری‌اکشن روزانه شما (۲۰ عدد) به پایان رسیده است."
            
    return True, "OK"

async def is_bot_admin(bot: Bot, channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False
