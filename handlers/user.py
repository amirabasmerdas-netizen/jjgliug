from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import config
import database as db
from services.quota import check_and_decrement_quota
from services.channel import is_bot_admin_in_channel

router = Router()

class ChannelState(StatesGroup):
    waiting_for_channel = State()
    waiting_for_post = State()

def get_main_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="خرید / تمدید پرو"), KeyboardButton(text="ارتباط با ادمین")],
        [KeyboardButton(text="راهنما"), KeyboardButton(text="ویو")],
        [KeyboardButton(text="ری‌اکشن")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@router.message(F.text == "/start")
async def cmd_start(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id)
    await message.answer(f"سلام {message.from_user.first_name}! به ربات مدیریت کانال خوش آمدید.", reply_markup=get_main_menu_kb())

@router.message(F.text == "ویو")
async def cmd_view(message: types.Message, state: FSMContext):
    user = await db.get_or_create_user(message.from_user.id)
    allowed, msg = await check_and_decrement_quota(user, 'view')
    if not allowed:
        await message.answer(msg)
        return
    
    await message.answer("لطفاً آیدی کانال خود را با @ ارسال کنید (مثال: @mychannel)\n\n⚠️ توجه: ربات باید در کانال شما ادمین باشد.")
    await state.set_state(ChannelState.waiting_for_channel)

@router.message(ChannelState.waiting_for_channel)
async def process_channel_id(message: types.Message, state: FSMContext, bot: types.Bot):
    channel_id = message.text.strip()
    is_admin = await is_bot_admin_in_channel(bot, channel_id)
    
    if not is_admin:
        await message.answer("❌ ربات در این کانال ادمین نیست. لطفاً ربات را ادمین کنید و دوباره تلاش کنید.")
        return

    # ذخیره در دیتابیس
    async with db.AsyncSessionLocal() as session:
        user = (await session.execute(db.User.__table__.select().where(db.User.telegram_id == message.from_user.id))).scalar_one()
        user.channel_id = channel_id
        user.channel_verified = True
        await session.commit()

    await message.answer("✅ کانال با موفقیت تأیید شد! حالا یک پست تستی از کانال خود به این ربات فوروارد کنید.")
    await state.set_state(ChannelState.waiting_for_post)

@router.message(ChannelState.waiting_for_post, F.forward_from_chat)
async def process_test_post(message: types.Message, bot: types.Bot):
    async with db.AsyncSessionLocal() as session:
        user = (await session.execute(db.User.__table__.select().where(db.User.telegram_id == message.from_user.id))).scalar_one()
        if user.user_type == 'normal':
            user.daily_views -= 1
            await session.commit()

    # فوروارد به گروه‌های هدف
    for group_id in config.TARGET_VIEW_GROUPS:
        try:
            await bot.copy_message(chat_id=group_id, from_chat_id=message.chat.id, message_id=message.message_id)
        except Exception:
            pass # مدیریت خطا در لاگ واقعی
    
    await message.answer("✅ پست با موفقیت در گروه‌های هدف قرار گرفت. سهمیه بازدید شما به‌روزرسانی شد.")
    await message.answer("منوی اصلی:", reply_markup=get_main_menu_kb())
    await state.clear()

@router.message(F.text == "ری‌اکشن")
async def cmd_reaction(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id)
    allowed, msg = await check_and_decrement_quota(user, 'reaction')
    if not allowed:
        await message.answer(msg)
        return

    # دریافت لیست ربات‌های کارگر فعال
    async with db.AsyncSessionLocal() as session:
        workers = (await session.execute(db.WorkerBot.__table__.select().where(db.WorkerBot.is_active == True))).scalars().all()
    
    if not workers:
        await message.answer("⚠️ در حال حاضر ربات ری‌اکشن‌دهنده‌ای فعال نیست. لطفاً با ادمین تماس بگیرید.")
        return

    worker_list = "\n".join([f"🤖 @{w.bot_username}" for w in workers])
    await message.answer(
        f"برای فعال‌سازی ری‌اکشن، مراحل زیر را انجام دهید:\n\n"
        f"1️⃣ آیدی کانال خود را ارسال کنید.\n"
        f"2️⃣ ربات‌های زیر را در کانال خود ادمین کنید:\n{worker_list}\n\n"
        f"پس از ادمین کردن، کلمه 'تأیید' را ارسال کنید."
    )
    # (ادامه منطق FSM برای تأیید نهایی و شروع فرآیند ری‌اکشن)

@router.message(F.text == "خرید / تمدید پرو")
async def cmd_buy_pro(message: types.Message):
    await message.answer(
        f"💎 برای خرید یا تمدید اشتراک پرو، لطفاً با ادمین در ارتباط باشید:\n\n"
        f"👤 آیدی ادمین: @{(await message.bot.get_chat(config.OWNER_ID)).username or 'Admin'}\n\n"
        f"پس از پرداخت، ادمین اشتراک شما را فعال خواهد کرد."
    )
