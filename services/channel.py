import re
from aiogram import Bot
import logging

logger = logging.getLogger(__name__)

async def is_bot_admin_in_channel(bot: Bot, channel_id: str) -> tuple[bool, str]:
    try:
        clean_id = channel_id.strip()
        
        # 🔥 پارسر هوشمند: تبدیل لینک تلگرام به یوزرنیم
        match = re.search(r"t\.me/([a-zA-Z0-9_]+)", clean_id)
        if match:
            clean_id = "@" + match.group(1)
        elif not clean_id.startswith('@') and not clean_id.startswith('-100'):
            clean_id = "@" + clean_id
            
        logger.info(f"Checking admin status for bot in channel: {clean_id}")
        
        member = await bot.get_chat_member(chat_id=clean_id, user_id=bot.id)
        if member.status in ['administrator', 'creator']:
            return True, "OK"
        else:
            return False, f"⚠️ ربات در کانال عضو است اما ادمین نیست. (وضعیت فعلی: {member.status})"
            
    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Error checking admin status for {channel_id}: {e}")
        
        # 🔥 نمایش پیام خطای دقیق به کاربر
        if "chat not found" in error_str:
            return False, "❌ کانال یافت نشد! مطمئن شوید آیدی را درست وارد کرده‌اید (برای کانال‌های عمومی با @ و برای خصوصی با آیدی عددی -100...)."
        elif "bot is not a member" in error_str:
            return False, "❌ ربات در این کانال عضو نیست. لطفاً ابتدا ربات را به کانال اضافه کرده و سپس ادمین کنید."
        else:
            return False, f"❌ خطا در بررسی دسترسی: {str(e)}"
