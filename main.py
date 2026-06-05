import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage # 🔥 اضافه شده برای کارکرد دکمه‌ها

import config
import database as db
from handlers import user, admin
from worker_manager import handle_worker_webhook

logging.basicConfig(level=logging.INFO)

async def on_startup(bot: Bot):
    webhook_url = f"{config.WEBHOOK_URL}{config.WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url, secret_token=config.SECRET_TOKEN)
    logging.info(f"Webhook set to {webhook_url}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook deleted")

async def uptime_robots_ping(request: web.Request):
    return web.Response(text="Bot is running and healthy!")

async def main():
    await db.init_db()
    
    bot = Bot(
        token=config.BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # 🔥 اصلاح حیاتی: اضافه کردن MemoryStorage برای کارکرد FSM (دکمه‌ها و مراحل)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.include_router(user.router)
    dp.include_router(admin.router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config.SECRET_TOKEN
    )
    webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)
    app.router.add_post('/worker_webhook/{token}', handle_worker_webhook)
    app.router.add_get('/', uptime_robots_ping)
    
    setup_application(app, dp, bot=bot)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logging.info(f"🚀 Server started successfully on port {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
