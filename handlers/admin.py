from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import config
import database as db
import requests

router = Router()

class AdminState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_worker_token = State()

@router.message(F.text == "پنل مدیریت")
async def cmd_admin_panel(message: types.Message):
    if message.from_user.id != config.OWNER_ID:
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ارتقا به پرو", callback_data="admin_upgrade")],
        [InlineKeyboardButton(text="ساخت ربات ری‌اکشن‌دهنده جدید", callback_data="admin_create_worker")],
        [InlineKeyboardButton(text="لیست کاربران", callback_data="admin_list_users")]
    ])
    await message.answer("🛠 پنل مدیریت مالک:", reply_markup=kb)

@router.callback_query(F.data == "admin_create_worker")
async def ask_worker_token(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("لطفاً توکن خام (Raw Token) ربات جدید را ارسال کنید:\n(مثال: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)")
    await state.set_state(AdminState.waiting_for_worker_token)
    await call.answer()

@router.message(AdminState.waiting_for_worker_token)
async def process_worker_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    
    # 1. بررسی اعتبار توکن با گرفتن اطلاعات ربات
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
        if not response.get("ok"):
            await message.answer("❌ توکن نامعتبر است. لطفاً دوباره تلاش کنید.")
            return
        bot_username = response["result"]["username"]
    except Exception:
        await message.answer("❌ خطا در ارتباط با تلگرام. توکن را بررسی کنید.")
        return

    # 2. تنظیم وب‌هوک برای این ربات کارگر به سرور Render ما
    webhook_url = f"{config.WEBHOOK_URL}/worker_webhook/{token}"
    try:
        wh_response = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url, "secret_token": config.SECRET_TOKEN}
        ).json()
        
        if not wh_response.get("ok"):
            await message.answer(f"❌ خطا در تنظیم وب‌هوک: {wh_response.get('description')}")
            return
    except Exception as e:
        await message.answer(f"❌ خطای شبکه: {str(e)}")
        return

    # 3. ذخیره در دیتابیس
    async with db.AsyncSessionLocal() as session:
        new_worker = db.WorkerBot(bot_token=token, bot_username=bot_username, is_active=True)
        session.add(new_worker)
        await session.commit()

    await message.answer(f"✅ ربات ری‌اکشن‌دهنده @{bot_username} با موفقیت ساخته و به لیست اضافه شد!")
    await state.clear()

# منطق ارتقا به پرو (ساده‌شده)
@router.callback_query(F.data.startswith("admin_set_pro_"))
async def set_pro_duration(call: types.CallbackQuery):
    # دریافت user_id و duration از callback data و به‌روزرسانی دیتابیس
    # duration می‌تواند '1w', '1m', '3m', '1y' باشد
    pass
