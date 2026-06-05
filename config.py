import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثلاً: https://your-app.onrender.com
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "my_secret_key")

# آیدی گروه‌هایی که پست‌ها باید به آن‌ها فوروارد شوند (برای سیستم ویو)
TARGET_VIEW_GROUPS = [-1003747486578, -1009876543210] 

DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")
