from aiohttp import web
import requests
import json
import database as db
import config  # 🔥 اضافه کردن ایمپورت config

async def handle_worker_webhook(request: web.Request):
    token = request.match_info['token']
    
    # 🔥 اصلاح: بررسی توکن امنیتی از طریق config
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != config.SECRET_TOKEN:
        return web.Response(status=401)

    # بررسی وجود توکن در دیتابیس
    async with db.AsyncSessionLocal() as session:
        worker = (await session.execute(db.WorkerBot.__table__.select().where(db.WorkerBot.bot_token == token))).scalar_one_or_none()
        if not worker or not worker.is_active:
            return web.Response(status=404)

    # دریافت آپدیت از تلگرام
    update = await request.json()
    
    # استخراج اطلاعات پیام (فقط اگر پیام در کانال باشد)
    if 'channel_post' in update or 'edited_channel_post' in update:
        post = update.get('channel_post') or update.get('edited_channel_post')
        chat_id = post['chat']['id']
        message_id = post['message_id']
        
        # ارسال ری‌اکشن با استفاده از توکن ربات کارگر
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": [{"type": "emoji", "emoji": "👍"}] # می‌تواند داینامیک باشد
        }
        
        try:
            requests.post(f"https://api.telegram.org/bot{token}/setMessageReaction", json=payload)
        except Exception as e:
            print(f"Error sending reaction: {e}")

    return web.Response(status=200)
