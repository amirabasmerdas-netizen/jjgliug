from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import config
import database as db
import requests
from sqlalchemy import update

router = Router()

class AdminState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_worker_token = State()

@router.callback_query(F.data == "admin_create_worker")
async def ask_worker_token(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.OWNER_ID:
        await call.answer("شما دسترسی ندارید!", show_alert=True)
        return
    await call.message.answer("لطفاً توکن خام (Raw Token) ربات جدید را ارسال کنید:\n(مثال: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)")
    await state.set_state(AdminState.waiting_for_worker_token)
    await call.answer()

@router.message(AdminState.waiting_for_worker_token)
async def process_worker_token(message: types.Message, state: FSMContext):
    if message.from_user.id != config.OWNER_ID:
        return
    token = message.text.strip()
    
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
        if not response.get("ok"):
            await message.answer("❌ توکن نامعتبر است. لطفاً دوباره تلاش کنید.")
            return
        bot_username = response["result"]["username"]
    except Exception:
        await message.answer("❌ خطا در ارتباط با تلگرام. توکن را بررسی کنید.")
        return

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

    async with db.AsyncSessionLocal() as session:
        new_worker = db.WorkerBot(bot_token=token, bot_username=bot_username, is_active=True)
        session.add(new_worker)
        await session.commit()

    await message.answer(f"✅ ربات ری‌اکشن‌دهنده @{bot_username} با موفقیت ساخته و به لیست اضافه شد!")
    await state.clear()

@router.callback_query(F.data == "admin_manage_user")
async def ask_user_to_upgrade(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.OWNER_ID:
        await call.answer("شما دسترسی ندارید!", show_alert=True)
        return
    await call.message.answer("لطفاً آیدی عددی کاربر را ارسال کنید:")
    await state.set_state(AdminState.waiting_for_user_id)
    await call.answer()

@router.message(AdminState.waiting_for_user_id)
async def process_user_upgrade(message: types.Message, state: FSMContext):
    if message.from_user.id != config.OWNER_ID:
        return
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ آیدی عددی نامعتبر است.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ارتقا به پرو (1 ماه)", callback_data=f"set_pro_{target_user_id}_1m")],
        [InlineKeyboardButton(text="ارتقا به پرو (3 ماه)", callback_data=f"set_pro_{target_user_id}_3m")],
        [InlineKeyboardButton(text="ارتقا به پرو (1 سال)", callback_data=f"set_pro_{target_user_id}_1y")],
        [InlineKeyboardButton(text="تنزل به کاربر عادی", callback_data=f"set_normal_{target_user_id}")],
    ])
    await message.answer(f"عملیات مورد نظر برای کاربر <code>{target_user_id}</code> را انتخاب کنید:", reply_markup=kb, parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("set_pro_"))
async def set_pro_duration(call: types.CallbackQuery):
    if call.from_user.id != config.OWNER_ID:
        await call.answer("شما دسترسی ندارید!", show_alert=True)
        return
    
    parts = call.data.split("_")
    target_user_id = int(parts[2])
    duration = parts[3]
    
    duration_map = {'1w': 7, '1m': 30, '3m': 90, '1y': 365}
    days = duration_map.get(duration, 30)
    expiry_date = datetime.utcnow() + timedelta(days=days)

    async with db.AsyncSessionLocal() as session:
        await session.execute(
            update(db.User).where(db.User.telegram_id == target_user_id).values(
                user_type='pro', pro_expiry=expiry_date
            )
        )
        await session.commit()
    
    await call.message.answer(f"✅ کاربر <code>{target_user_id}</code> به مدت {days} روز به حالت پرو ارتقا یافت.", parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("set_normal_"))
async def set_normal_user(call: types.CallbackQuery):
    if call.from_user.id != config.OWNER_ID:
        await call.answer("شما دسترسی ندارید!", show_alert=True)
        return
    
    target_user_id = int(call.data.split("_")[2])
    async with db.AsyncSessionLocal() as session:
        await session.execute(
            update(db.User).where(db.User.telegram_id == target_user_id).values(user_type='normal')
        )
        await session.commit()
    
    await call.message.answer(f"✅ کاربر <code>{target_user_id}</code> به کاربر عادی تنزل یافت.", parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "admin_list_users")
async def list_users(call: types.CallbackQuery):
    if call.from_user.id != config.OWNER_ID:
        await call.answer("شما دسترسی ندارید!", show_alert=True)
        return
    
    async with db.AsyncSessionLocal() as session:
        users = (await session.execute(db.User.__table__.select())).scalars().all()
    
    if not users:
        await call.message.answer("هیچ کاربری در سیستم ثبت نشده است.")
        await call.answer()
        return

    text = "📊 <b>لیست کاربران:</b>\n\n"
    for u in users[:10]: # نمایش 10 کاربر اول برای جلوگیری از طولانی شدن پیام
        status = "💎 پرو" if u.user_type == 'pro' else ("👑 ادمین" if u.user_type == 'owner' else "👤 عادی")
        text += f"🆔 <code>{u.telegram_id}</code> | {status}\n"
    
    if len(users) > 10:
        text += f"\n... و {len(users) - 10} کاربر دیگر."
    
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()
