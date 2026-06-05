from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import update
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

def get_admin_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="پنل مدیریت ⚙️")],
        [KeyboardButton(text="راهنما"), KeyboardButton(text="ویو")],
        [KeyboardButton(text="ری‌اکشن"), KeyboardButton(text="خرید / تمدید پرو")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@router.message(F.text == "/start")
async def cmd_start(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id)
    
    # 🔥 شناسایی مالک و به‌روزرسانی دیتابیس
    if message.from_user.id == config.OWNER_ID and user.user_type != 'owner':
        async with db.AsyncSessionLocal() as session:
            await session.execute(
                update(db.User).where(db.User.telegram_id == message.from_user.id).values(user_type='owner')
            )
            await session.commit()
        user.user_type = 'owner'

    if user.user_type == 'owner':
        await message.answer("سلام ادمین عزیز! به پنل مدیریت خوش آمدید.", reply_markup=get_admin_menu_kb())
    else:
        await message.answer(f"سلام {message.from_user.first_name}! به ربات مدیریت کانال خوش آمدید.", reply_markup=get_main_menu_kb())

@router.message(F.text == "پنل مدیریت ⚙️")
async def cmd_admin_panel_redirect(message: types.Message):
    if message.from_user.id != config.OWNER_ID:
        await message.answer("شما دسترسی به این بخش را ندارید.")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="مدیریت کاربران (ارتقا/تنزل)", callback_data="admin_manage_user")],
        [InlineKeyboardButton(text="ساخت ربات ری‌اکشن‌دهنده جدید", callback_data="admin_create_worker")],
        [InlineKeyboardButton(text="لیست کاربران", callback_data="admin_list_users")]
    ])
    await message.answer("🛠 پنل مدیریت مالک:", reply_markup=kb)

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

    async with db.AsyncSessionLocal() as session:
        await session.execute(
            update(db.User).where(db.User.telegram_id == message.from_user.id).values(
                channel_id=channel_id, channel_verified=True
            )
        )
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

    for group_id in config.TARGET_VIEW_GROUPS:
        try:
            await bot.copy_message(chat_id=group_id, from_chat_id=message.chat.id, message_id=message.message_id)
        except Exception:
            pass
    
    await message.answer("✅ پست با موفقیت در گروه‌های هدف قرار گرفت. سهمیه بازدید شما به‌روزرسانی شد.")
    
    # بازگشت به منوی مناسب بر اساس نوع کاربر
    current_user = await db.get_or_create_user(message.from_user.id)
    kb = get_admin_menu_kb() if current_user.user_type == 'owner' else get_main_menu_kb()
    await message.answer("منوی اصلی:", reply_markup=kb)
    await state.clear()

@router.message(F.text == "ری‌اکشن")
async def cmd_reaction(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id)
    allowed, msg = await check_and_decrement_quota(user, 'reaction')
    if not allowed:
        await message.answer(msg)
        return

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

@router.message(F.text == "ارتباط با ادمین")
async def cmd_contact_admin(message: types.Message):
    try:
        admin_chat = await message.bot.get_chat(config.OWNER_ID)
        username = admin_chat.username or "Admin"
        await message.answer(f"📞 برای ارتباط با ادمین، به آیدی زیر پیام دهید:\n\n👤 @{username}")
    except Exception:
        await message.answer(f"📞 برای ارتباط با ادمین، به آیدی عددی زیر پیام دهید:\n\n👤 {config.OWNER_ID}")

@router.message(F.text == "راهنما")
async def cmd_help(message: types.Message):
    help_text = (
        "📖 <b>راهنمای استفاده از ربات:</b>\n\n"
        "🔹 <b>ویو:</b> افزایش بازدید پست‌های کانال شما.\n"
        "🔹 <b>ری‌اکشن:</b> افزایش ری‌اکشن پست‌های کانال شما.\n"
        "🔹 <b>خرید / تمدید پرو:</b> مشاهده اطلاعات خرید اشتراک ویژه.\n\n"
        "⚠️ <b>توجه:</b> کاربران عادی روزانه ۲۰ بازدید و ۲۰ ری‌اکشن رایگان دارند.\n"
        "برای دسترسی نامحدود، اشتراک پرو تهیه کنید."
    )
    await message.answer(help_text)

@router.message(F.text == "خرید / تمدید پرو")
async def cmd_buy_pro(message: types.Message):
    try:
        admin_chat = await message.bot.get_chat(config.OWNER_ID)
        username = admin_chat.username or "Admin"
        admin_link = f"@{username}"
    except Exception:
        admin_link = str(config.OWNER_ID)

    await message.answer(
        f"💎 برای خرید یا تمدید اشتراک پرو، لطفاً با ادمین در ارتباط باشید:\n\n"
        f"👤 آیدی ادمین: {admin_link}\n\n"
        f"پس از پرداخت، ادمین اشتراک شما را فعال خواهد کرد."
    )
