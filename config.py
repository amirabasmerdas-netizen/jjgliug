import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0")) # جلوگیری از کرش در صورت ست نبودن OWNER_ID

# 🔥 اصلاح: حذف اسلش انتهایی آدرس وب‌هوک (بسیار مهم)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip('/')  
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# 🔥 اصلاح: استفاده از یک توکن پیش‌فرض کاملاً استاندارد (فقط حروف و اعداد انگلیسی)
# اگر در Render متغیر SECRET_TOKEN را ست کرده‌اید، مطمئن شوید که هیچ فاصله یا کاراکتر عجیبی ندارد.
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SuperSecretToken1234567890")

# آیدی گروه‌هایی که پست‌ها باید به آن‌ها فوروارد شوند (برای سیستم ویو)
TARGET_VIEW_GROUPS = [-1003747486578, -1009876543210] 

DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")
