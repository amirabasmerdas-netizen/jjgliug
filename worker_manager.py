from aiohttp import web, ClientSession
import database as db
import config
import logging

logger = logging.getLogger(__name__)

async def handle_worker_webhook(request: web.Request):
    token = request.match_info['token']
    
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != config.SECRET_TOKEN:
        return web.Response(status=401)

    async with db.AsyncSessionLocal() as session:
        worker = (await session.execute(db.WorkerBot.__table__.select().where(db.WorkerBot.bot_token == token))).scalar_one_or_none()
        if not worker or not worker.is_active:
            return web.Response(status=404)

    update = await request.json()
    
    if 'channel_post' in update or 'edited_channel_post' in update:
        post = update.get('channel_post') or update.get('edited_channel_post')
        chat_id = post['chat']['id']
        message_id = post['message_id']
        
        logger.info(f"Worker {worker.bot_username} received post in {chat_id}")
        
        # 🔥 استفاده از ClientSession برای جلوگیری از مسدود شدن سرور
        async with ClientSession() as session_req:
            try:
                # 1. دریافت لیست تمام ری‌اکشن‌های فعال کانال مقصد
                get_chat_url = f"https://api.telegram.org/bot{token}/getChat"
                async with session_req.post(get_chat_url, json={"chat_id": chat_id}) as resp:
                    chat_info = await resp.json()
                
                if chat_info.get("ok"):
                    available_reactions = chat_info["result"].get("available_reactions", [])
                    
                    # فیلتر کردن فقط ایموجی‌های استاندارد (ربات‌ها معمولاً به کاستوم ایموجی‌ها دسترسی ندارند)
                    valid_reactions = [r for r in available_reactions if r.get('type') == 'emoji']
                    
                    if valid_reactions:
                        logger.info(f"Applying {len(valid_reactions)} reactions to {chat_id}/{message_id}")
                        
                        # 2. ارسال تمام ری‌اکشن‌های موجود در کانال به صورت یکجا
                        payload = {
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "reaction": valid_reactions,
                            "is_big": True  # انیمیشن ری‌اکشن را بزرگتر و جذاب‌تر می‌کند
                        }
                        react_url = f"https://api.telegram.org/bot{token}/setMessageReaction"
                        async with session_req.post(react_url, json=payload) as react_resp:
                            res = await react_resp.json()
                            if not res.get("ok"):
                                logger.error(f"Reaction failed: {res}")
                            else:
                                logger.info(f"Reaction sent successfully by {worker.bot_username}")
                    else:
                        logger.warning(f"No standard emoji reactions available for {chat_id}")
                else:
                    logger.error(f"getChat failed: {chat_info}")
                    
            except Exception as e:
                logger.error(f"Error processing reaction: {e}")

    return web.Response(status=200)
