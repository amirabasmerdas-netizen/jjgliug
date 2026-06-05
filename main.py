import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import config
import database as db
from handlers import user, admin
from worker_manager import handle_worker_webhook

logging.basicConfig(level=logging.INFO)

async def on_startup(bot: Bot):
    """تنظیم وب‌هوک ربات اصلی هنگام شروع به کار سرور"""
    webhook_url = f"{config.WEBHOOK_URL}{config.WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url, secret_token=config.SECRET_TOKEN)
    logging.info(f"Webhook set to {webhook_url}")

async def on_shutdown(bot: Bot):
    """حذف وب‌هوک هنگام توقف سرور"""
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook deleted")

async def uptime_robots_ping(request: web.Request):
    """اندپوینت برای بیدار نگه داشتن سرور توسط UptimeRobot"""
    return web.Response(text="Bot is running and healthy!")

async def main():
    # 1. مقداردهی اولیه دیتابیس
    await db.init_db()
    
    # 2. ساخت ربات اصلی با استفاده از DefaultBotProperties (اصلاح خطای parse_mode)
    bot = Bot(
        token=config.BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # 3. ثبت روترهای هندلرها
    dp.include_router(user.router)
    dp.include_router(admin.router)
    
    # 4. ثبت توابع شروع و پایان
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # 5. تنظیم سرور Aiohttp
    app = web.Application()
    
    # مسیر وب‌هوک ربات اصلی
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config.SECRET_TOKEN
    )
    webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)
    
    # مسیر وب‌هوک داینامیک برای ربات‌های کارگر
    app.router.add_post('/worker_webhook/{token}', handle_worker_webhook)
    
    # مسیر برای پینگ UptimeRobot
    app.router.add_get('/', uptime_robots_ping)
    
    setup_application(app, dp, bot=bot)
    
    # 6. اجرای سرور
    runner = web.AppRunner(app)
    await runner.setup()
    
    # 🔥 اصلاح خطای پورت: استفاده از متغیر محیطی PORT که Render اختصاص می‌دهد
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logging.info(f"🚀 Server started successfully on port {port}")
    
    # نگه‌داشتن فرآیند در حال اجرا
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
