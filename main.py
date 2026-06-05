# main.py
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.webhook.security import IPFilter
import config
import database as db
from handlers import user, admin
from worker_manager import handle_worker_webhook

logging.basicConfig(level=logging.INFO)

async def on_startup(bot: Bot):
    await bot.set_webhook(f"{config.WEBHOOK_URL}{config.WEBHOOK_PATH}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

async def uptime_robots_ping(request: web.Request):
    """این اندپوینت توسط UptimeRobot پینگ می‌شود تا سرور Render بیدار بماند."""
    return web.Response(text="Bot is running and healthy!")

async def main():
    await db.init_db()
    
    bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    
    # ثبت روترها
    dp.include_router(user.router)
    dp.include_router(admin.router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # تنظیم سرور Aiohttp
    app = web.Application()
    
    # 1. مسیر وب‌هوک ربات اصلی
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config.SECRET_TOKEN
    )
    webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)
    
    # 2. مسیر وب‌هوک داینامیک برای ربات‌های کارگر
    app.router.add_post('/worker_webhook/{token}', handle_worker_webhook)
    
    # 3. مسیر برای بیدار نگه داشتن Render توسط UptimeRobot
    app.router.add_get('/', uptime_robots_ping)
    
    setup_application(app, dp, bot=bot)
    
    # اجرای سرور
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080) # Render پورت 8080 را اکسپوز می‌کند
    await site.start()
    
    # نگه‌داشتن فرآیند در حال اجرا
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
