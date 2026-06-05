from aiohttp import web, ClientSession
import database as db
import config
import logging

logger = logging.getLogger(__name__)

async def handle_worker_webhook(request: web.Request):
    token = request.match_info['token']
    
    # بررسی امنیت وب‌هوک
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != config.SECRET_TOKEN:
        return web.Response(status=401)

    # بررسی وجود ربات در دیتابیس
    async with db.AsyncSessionLocal() as session:
        worker = (await session.execute(db.WorkerBot.__table__.select().where(db.WorkerBot.bot_token == token))).scalar_one_or_none()
        if not worker or not worker.is_active:
            return web.Response(status=404)

    update = await request.json()
    
    # اگر پست جدیدی در کانال آمد (معادل channel_post در کد شما)
    if 'channel_post' in update or 'edited_channel_post' in update:
        post = update.get('channel_post') or update.get('edited_channel_post')
        chat_id = post['chat']['id']
        message_id = post['message_id']
        
        logger.info(f"Worker {worker.bot_username} received post in {chat_id}")
        
        # 🔥 منطق دقیقاً بر اساس کد شما، اما به صورت Async برای Render
        async with ClientSession() as session_req:
            try:
                # 1. دریافت لیست ری‌اکشن‌های فعال کانال (برای زدن همه ری‌اکشن‌ها)
                get_chat_url = f"https://api.telegram.org/bot{token}/getChat"
                async with session_req.post(get_chat_url, json={"chat_id": chat_id}) as resp:
                    chat_info = await resp.json()
                
                if chat_info.get("ok"):
                    # استخراج ری‌اکشن‌های استاندارد (ایموجی‌ها)
                    available_reactions = chat_info["result"].get("available_reactions", [])
                    valid_reactions = [r for r in available_reactions if r.get('type') == 'emoji']
                    
                    if valid_reactions:
                        # 2. ارسال ری‌اکشن (دقیقاً با ساختار کد شما)
                        url = f"https://api.telegram.org/bot{token}/setMessageReaction"
                        data = {
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "reaction": valid_reactions  # به جای یک ایموجی، همه ری‌اکشن‌های کانال
                        }
                        
                        # دقیقاً معادل requests.post(url, json=data) در کد شما
                        async with session_req.post(url, json=data) as react_resp:
                            res = await react_resp.json()
                            if res.get("ok"):
                                logger.info(f"Reaction sent by {worker.bot_username}")
                            else:
                                logger.error(f"Reaction failed: {res}")
                    else:
                        logger.warning(f"No standard emoji reactions available for {chat_id}")
                else:
                    logger.error(f"getChat failed: {chat_info}")
                    
            except Exception as e:
                # معادل except Exception as e: print(e) در کد شما
                logger.error(f"Error sending reaction: {e}")

    return web.Response(status=200)
