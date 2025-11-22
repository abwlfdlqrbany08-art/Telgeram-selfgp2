
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)
import pytz
from datetime import datetime
import logging
import json
import os
import random
import string
import asyncio

TOKEN = "8529252982:AAF_m05kDlPCrT9sMtDc_l-mXK_iibM9l6Q"
ADMIN_IDS = [7544529139]
DATA_FILE = "bot_data.json"

REFERRAL_POINTS = 5
CHANNEL_POINTS = 10

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    user_channels = data.get('user_channels', {})
    banned_users = set(data.get('banned_users', []))
    user_points = data.get('user_points', {})
    referral_codes = data.get('referral_codes', {})
    used_referrals = data.get('used_referrals', {})
    channel_points = data.get('channel_points', CHANNEL_POINTS)
else:
    user_channels = {}
    banned_users = set()
    user_points = {}
    referral_codes = {}
    used_referrals = {}
    channel_points = CHANNEL_POINTS

active_tasks = {}

FONT_STYLES = {
    "پررنگ": "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
    "دوبل": "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡", 
    "ساده": "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵",
    "تک‌فاصله": "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿",
    "پیش‌فرض": "0123456789",
}

def save_data():
    data = {
        'user_channels': user_channels,
        'banned_users': list(banned_users),
        'user_points': user_points,
        'referral_codes': referral_codes,
        'used_referrals': used_referrals,
        'channel_points': channel_points
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def generate_referral_code(user_id: int) -> str:
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    referral_codes[code] = user_id
    save_data()
    return code

def convert_to_font(time_str: str, font_style: str) -> str:
    if font_style not in FONT_STYLES:
        return time_str
    
    font_digits = FONT_STYLES[font_style]
    normal_digits = "0123456789"
    translation_table = str.maketrans(normal_digits, font_digits)
    return time_str.translate(translation_table)

async def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_main_keyboard(user_id):
    if user_id in ADMIN_IDS:
        return ReplyKeyboardMarkup([
            ["➕ ثبت کانال/گروه", "🗑 حذف کانال/گروه"],
            ["🖋 تغییر فونت", "🎁 سیستم امتیاز"],
            ["📝 تنظیم بیوگرافی", "⚙️ تنظیمات زمان"],
            ["📊 لینک رفرال من", "🛠 پنل مدیریت"],
            ["📈 آمار کاربری", "ℹ️ راهنما"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["➕ ثبت کانال/گروه", "🗑 حذف کانال/گروه"],
            ["🖋 تغییر فونت", "🎁 سیستم امتیاز"], 
            ["📝 تنظیم بیوگرافی", "⚙️ تنظیمات زمان"],
            ["📊 لینک رفرال من", "📈 آمار کاربری"],
            ["ℹ️ راهنما"]
        ], resize_keyboard=True)

def get_admin_keyboard():
    return ReplyKeyboardMarkup([
        ["📊 آمار ربات", "🚫 بن کاربر"],
        ["✅ آنبن کاربر", "📋 لیست کانال‌ها"],
        ["🎯 مدیریت امتیازها", "⚙️ تنظیم امتیاز"],
        ["🔙 بازگشت به منوی اصلی"]
    ], resize_keyboard=True)

def get_font_keyboard():
    return ReplyKeyboardMarkup([
        ["𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟡 پررنگ", "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡 دوبل"],
        ["𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵 ساده", "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿 تک‌فاصله"],
        ["0123456789 پیش‌فرض", "🔙 بازگشت"]
    ], resize_keyboard=True)

def get_time_settings_keyboard():
    return ReplyKeyboardMarkup([
        ["⏰ فعال کردن زمان در نام", "⏰ غیرفعال کردن زمان در نام"],
        ["📝 فعال کردن زمان در بیوگرافی", "📝 غیرفعال کردن زمان در بیوگرافی"],
        ["🔙 بازگشت"]
    ], resize_keyboard=True)

def get_channel_selection_keyboard(user_id):
    if user_id not in user_channels or not user_channels[user_id]:
        return None
    
    keyboard = []
    for channel_id, data in user_channels[user_id].items():
        keyboard.append([f"📢 {data['base_name']} (ID: {channel_id})"])
    keyboard.append(["🔙 بازگشت"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user = update.effective_user
    args = context.args
    
    if user.id in banned_users:
        await update.message.reply_text(
            "⛔ شما از استفاده از این ربات محروم شده‌اید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if user.id not in referral_codes.values():
        generate_referral_code(user.id)
    
    if args and args[0] in referral_codes:
        referral_code = args[0]
        referrer_id = referral_codes[referral_code]
        
        if user.id == referrer_id:
            await update.message.reply_text(
                "❌ نمی‌توانید از کد رفرال خودتان استفاده کنید!",
                reply_markup=get_main_keyboard(user.id)
            )
            return
            
        if user.id in used_referrals:
            await update.message.reply_text(
                "❌ شما قبلاً از یک کد رفرال استفاده کرده‌اید!",
                reply_markup=get_main_keyboard(user.id)
            )
            return
            
        used_referrals[user.id] = referrer_id
        user_points[referrer_id] = user_points.get(referrer_id, 0) + REFERRAL_POINTS
        user_points[user.id] = user_points.get(user.id, 0) + REFERRAL_POINTS
        save_data()
        
        await update.message.reply_text(
            f"🎉 کد رفرال با موفقیت اعمال شد!\n\n"
            f"✅ شما {REFERRAL_POINTS} امتیاز دریافت کردید\n"
            f"✅ معرف شما هم {REFERRAL_POINTS} امتیاز گرفت",
            reply_markup=get_main_keyboard(user.id)
        )
    
    points = user_points.get(user.id, 0)
    
    welcome_text = f"""
👋 سلام {user.first_name}!

🤖 به ربات مدیریت زمان کانال/گروه خوش آمدید

🏆 امتیاز شما: {points} امتیاز

📌 امکانات ربات:
• ⏰ نمایش زمان زنده در نام کانال/گروه
• 📝 نمایش زمان زنده در بیوگرافی  
• 🎯 سیستم امتیازدهی هوشمند  
• 📊 لینک رفرال اختصاصی
• 🎨 فونت‌های متنوع زمان
• 👥 مدیریت چندین کانال/گروه

💡 از دکمه‌های زیر برای استفاده از ربات انتخاب کنید:
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(user.id),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user = update.effective_user
    message_text = update.message.text.strip()
    
    if user.id in banned_users:
        await update.message.reply_text("⛔ شما از استفاده از این ربات محروم شده‌اید.")
        return
    
    if message_text == "➕ ثبت کانال/گروه":
        await add_channel_start(update, context)
    
    elif message_text == "🗑 حذف کانال/گروه":
        await remove_channel_start(update, context)
    
    elif message_text == "🖋 تغییر فونت":
        await set_font_start(update, context)
    
    elif message_text == "📝 تنظیم بیوگرافی":
        await set_bio_start(update, context)
    
    elif message_text == "⚙️ تنظیمات زمان":
        await time_settings_start(update, context)
    
    elif message_text == "🎁 سیستم امتیاز":
        await points_system(update, context)
    
    elif message_text == "📊 لینک رفرال من":
        await my_referral(update, context)
    
    elif message_text == "🛠 پنل مدیریت":
        await admin_panel(update, context)
    
    elif message_text == "📈 آمار کاربری":
        await user_stats(update, context)
    
    elif message_text == "ℹ️ راهنما":
        await show_help(update, context)
    
    elif message_text == "🔙 بازگشت به منوی اصلی":
        await start(update, context)
    
    elif message_text == "📊 آمار ربات":
        await show_stats(update, context)
    
    elif message_text == "🚫 بن کاربر":
        await ban_user_start(update, context)
    
    elif message_text == "✅ آنبن کاربر":
        await unban_user_start(update, context)
    
    elif message_text == "📋 لیست کانال‌ها":
        await channel_list(update, context)
    
    elif message_text == "🎯 مدیریت امتیازها":
        await manage_points_start(update, context)
    
    elif message_text == "⚙️ تنظیم امتیاز":
        await set_channel_points_start(update, context)
    
    elif message_text in ["⏰ فعال کردن زمان در نام", "⏰ غیرفعال کردن زمان در نام", 
                         "📝 فعال کردن زمان در بیوگرافی", "📝 غیرفعال کردن زمان در بیوگرافی"]:
        await handle_time_settings(update, context, message_text)
    
    elif context.user_data.get("selecting_channel"):
        await handle_channel_selection(update, context, message_text)
    
    elif any(font in message_text for font in ["پررنگ", "دوبل", "ساده", "تک‌فاصله", "پیش‌فرض"]):
        await handle_font_selection(update, context, message_text)
    
    elif context.user_data.get("awaiting_channel_id"):
        await handle_channel_id(update, context, message_text)
    
    elif context.user_data.get("awaiting_base_name"):
        await handle_base_name(update, context, message_text)
    
    elif context.user_data.get("awaiting_bio_text"):
        await handle_bio_text(update, context, message_text)
    
    elif context.user_data.get("awaiting_points"):
        await handle_points_management(update, context, message_text)
    
    elif context.user_data.get("awaiting_ban"):
        await handle_ban_user(update, context, message_text)
    
    elif context.user_data.get("awaiting_unban"):
        await handle_unban_user(update, context, message_text)
    
    elif context.user_data.get("awaiting_channel_points"):
        await handle_channel_points(update, context, message_text)
    
    elif context.user_data.get("awaiting_channel_remove"):
        await handle_channel_remove(update, context, message_text)
    
    else:
        await update.message.reply_text(
            "❌ دستور نامعتبر! لطفاً از دکمه‌های زیر استفاده کنید:",
            reply_markup=get_main_keyboard(user.id)
        )

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    current_points = user_points.get(user_id, 0)
    if current_points < channel_points:
        await update.message.reply_text(
            f"❌ امتیاز کافی ندارید!\n\n"
            f"💎 برای ثبت کانال/گروه به {channel_points} امتیاز نیاز دارید\n"
            f"🏆 امتیاز فعلی شما: {current_points}\n\n"
            f"📨 می‌توانید با معرفی دوستان از طریق سیستم رفرال امتیاز کسب کنید.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "📝 ثبت کانال/گروه جدید\n\n"
        "لطفاً آیدی عددی کانال/گروه را ارسال کنید:\n\n"
        "📌 مثال:\n"
        "`-1001234567890`\n\n"
        "🔍 روش دریافت آیدی:\n"
        "• یک پیام از کانال/گروه به @RawDataBot فوروارد کنید\n"
        "• عدد مقابل `chat_id` را کپی کنید\n\n"
        "❌ برای لغو: /cancel",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    context.user_data["awaiting_channel_id"] = True

async def handle_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: str):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    try:
        chat = await context.bot.get_chat(chat_id=chat_id)
        chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        
        if chat.type not in ['channel', 'group', 'supergroup']:
            await update.message.reply_text(
                "❌ فقط کانال‌ها و گروه‌ها پشتیبانی می‌شوند!",
                reply_markup=get_main_keyboard(user_id)
            )
            return
            
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "❌ شما مدیر این کانال/گروه نیستید!\n\n"
                "📋 شرایط لازم:\n"
                "• شما باید مدیر کانال/گروه باشید\n"
                "• ربات را به عنوان مدیر اضافه کرده باشید\n"
                "• تمام دسترسی‌ها را به ربات داده باشید",
                reply_markup=get_main_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
            
        context.user_data["temp_channel_id"] = chat_id
        context.user_data["awaiting_channel_id"] = False
        context.user_data["awaiting_base_name"] = True
        
        await update.message.reply_text(
            "✅ کانال/گروه با موفقیت تأیید شد!\n\n"
            "📝 لطفاً نام پایه را ارسال کنید (بدون زمان):\n\n"
            "📌 مثال:\n"
            "`کانال رسمی`\n"
            "`گروه دوستان`\n"
            "`Community`\n\n"
            "💡 این نام به همراه زمان نمایش داده می‌شود\n"
            "❌ برای لغو: /cancel",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"خطا در تأیید کانال: {e}")
        await update.message.reply_text(
            f"❌ خطا در دسترسی به کانال/گروه!\n\n"
            f"🔧 علت ممکن:\n"
            f"• ربات را به کانال/گروه اضافه نکرده‌اید\n"
            f"• ربات را به عنوان مدیر تنظیم نکرده‌اید\n"
            f"• از آیدی عددی استفاده نکرده‌اید\n\n"
            f"📋 خطای فنی: {str(e)}",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )

async def handle_base_name(update: Update, context: ContextTypes.DEFAULT_TYPE, base_name: str):
    if update.effective_chat.type != "private":
        return
    
    channel_id = context.user_data["temp_channel_id"]
    user_id = update.effective_user.id
    
    user_points[user_id] = user_points.get(user_id, 0) - channel_points
    
    if user_id not in user_channels:
        user_channels[user_id] = {}
        
    user_channels[user_id][channel_id] = {
        "base_name": base_name,
        "font_style": "پیش‌فرض",
        "bio_text": "",
        "use_name_time": True,
        "use_bio_time": False
    }
    save_data()
    
    task_key = f"{user_id}_{channel_id}"
    if task_key not in active_tasks:
        task = asyncio.create_task(update_channel_loop(context.bot, channel_id, user_id))
        active_tasks[task_key] = task
    
    await update.message.reply_text(
        f"🎉 کانال/گروه با موفقیت ثبت شد!\n\n"
        f"📌 مشخصات:\n"
        f"• 🆔 آیدی: `{channel_id}`\n"
        f"• 📝 نام پایه: {base_name}\n"
        f"• ⭐ امتیاز کسر شده: -{channel_points}\n"
        f"• 🏆 امتیاز باقیمانده: {user_points.get(user_id, 0)}\n"
        f"• ⏰ آپدیت زمان: هر ۵ ثانیه\n"
        f"• 🎯 زمان در نام: فعال ✅\n"
        f"• 📝 زمان در بیوگرافی: غیرفعال ❌\n\n"
        f"✅ از همین لحظه زمان به صورت زنده نمایش داده می‌شود\n\n"
        f"⚙️ می‌توانید از منوی 'تنظیمات زمان' نمایش زمان را مدیریت کنید",
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )
    
    del context.user_data["temp_channel_id"]
    del context.user_data["awaiting_base_name"]

async def remove_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    if user_id not in user_channels or not user_channels[user_id]:
        await update.message.reply_text(
            "📭 شما هیچ کانال/گروهی ثبت نکرده‌اید.",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    channels_list = ""
    for i, (channel_id, data) in enumerate(user_channels[user_id].items(), 1):
        channels_list += f"{i}. {data['base_name']} (ID: {channel_id})\n"
    
    await update.message.reply_text(
        f"🗑 حذف کانال/گروه\n\n"
        f"📋 کانال‌ها/گروه‌های شما:\n{channels_list}\n"
        f"لطفاً آیدی کانال/گروه مورد نظر برای حذف را ارسال کنید:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    context.user_data["awaiting_channel_remove"] = True

async def handle_channel_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: str):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    try:
        if user_id in user_channels and channel_id in user_channels[user_id]:
            channel_name = user_channels[user_id][channel_id]["base_name"]
            
            del user_channels[user_id][channel_id]
            if not user_channels[user_id]:
                del user_channels[user_id]
            
            save_data()
            
            task_key = f"{user_id}_{channel_id}"
            if task_key in active_tasks:
                active_tasks[task_key].cancel()
                del active_tasks[task_key]
            
            try:
                await context.bot.set_chat_title(
                    chat_id=int(channel_id), 
                    title=channel_name
                )
                await context.bot.set_chat_description(
                    chat_id=int(channel_id), 
                    description=""
                )
            except Exception as e:
                logger.warning(f"خطا در بازگردانی نام کانال: {e}")
            
            await update.message.reply_text(
                f"✅ کانال/گروه '{channel_name}' با موفقیت حذف شد.",
                reply_markup=get_main_keyboard(user_id)
            )
        else:
            await update.message.reply_text(
                "❌ کانال/گروه مورد نظر یافت نشد!",
                reply_markup=get_main_keyboard(user_id)
            )
    
    except Exception as e:
        logger.error(f"خطا در حذف کانال: {e}")
        await update.message.reply_text(
            f"❌ خطا در حذف کانال: {str(e)}",
            reply_markup=get_main_keyboard(user_id)
        )
    finally:
        del context.user_data["awaiting_channel_remove"]

async def set_font_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    if user_id not in user_channels or not user_channels[user_id]:
        await update.message.reply_text(
            "📭 شما هیچ کانال/گروهی ثبت نکرده‌اید.",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    keyboard = get_channel_selection_keyboard(user_id)
    if not keyboard:
        await update.message.reply_text(
            "📭 شما هیچ کانال/گروهی ثبت نکرده‌اید.",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    await update.message.reply_text(
        "🎨 تغییر فونت زمان\n\n"
        "لطفاً کانال/گروه مورد نظر را انتخاب کنید:",
        reply_markup=keyboard
    )
    context.user_data["selecting_channel"] = True
    context.user_data["selection_type"] = "font"

async def set_bio_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    if user_id not in user_channels or not user_channels[user_id]:
        await update.message.reply_text(
            "📭 شما هیچ کانال/گروهی ثبت نکرده‌اید.",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    keyboard = get_channel_selection_keyboard(user_id)
    if not keyboard:
        await update.message.reply_text(
            "📭 شما هیچ کانال/گروهی ثبت نکرده‌اید.",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    await update.message.reply_text(
        "📝 تنظیم بیوگرافی کانال/گروه\n\n"
        "لطفاً کانال/گروه مورد نظر را انتخاب کنید:",
        reply_markup=keyboard
    )
    context.user_data["selecting_channel"] = True
    context.user_data["selection_type"] = "bio"

async def time_settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    if user_id not in user_channels or not user_channels[user_id]:
        await update.message.reply_text(
            "📭 شما هیچ کانال/گروهی ثبت نکرده‌اید.",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    keyboard = get_channel_selection_keyboard(user_id)
    if not keyboard:
        await update.message.reply_text(
            "📭 شما هیچ کانال/گروهی ثبت نکرده‌اید.",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    await update.message.reply_text(
        "⚙️ تنظیمات نمایش زمان\n\n"
        "لطفاً کانال/گروه مورد نظر را انتخاب کنید:",
        reply_markup=keyboard
    )
    context.user_data["selecting_channel"] = True
    context.user_data["selection_type"] = "time_settings"

async def handle_channel_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    user_id = update.effective_user.id
    
    if message_text == "🔙 بازگشت":
        await start(update, context)
        del context.user_data["selecting_channel"]
        if "selection_type" in context.user_data:
            del context.user_data["selection_type"]
        return
    
    selected_channel_id = None
    for channel_id, data in user_channels[user_id].items():
        if f"📢 {data['base_name']} (ID: {channel_id})" == message_text:
            selected_channel_id = channel_id
            break
    
    if not selected_channel_id:
        await update.message.reply_text(
            "❌ کانال انتخاب شده نامعتبر است!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    context.user_data["selected_channel_id"] = selected_channel_id
    selection_type = context.user_data["selection_type"]
    
    if selection_type == "time_settings":
        del context.user_data["selecting_channel"]
        del context.user_data["selection_type"]
        
        channel_data = user_channels[user_id][selected_channel_id]
        use_name = channel_data.get("use_name_time", True)
        use_bio = channel_data.get("use_bio_time", False)
        
        await update.message.reply_text(
            f"⚙️ تنظیمات زمان برای {channel_data['base_name']}\n\n"
            f"🎯 وضعیت فعلی:\n"
            f"• زمان در نام: {'فعال ✅' if use_name else 'غیرفعال ❌'}\n"
            f"• زمان در بیوگرافی: {'فعال ✅' if use_bio else 'غیرفعال ❌'}\n\n"
            f"لطفاً تنظیم مورد نظر را انتخاب کنید:",
            reply_markup=get_time_settings_keyboard(),
            parse_mode='Markdown'
        )
    elif selection_type == "font":
        del context.user_data["selecting_channel"]
        del context.user_data["selection_type"]
        
        await update.message.reply_text(
            "🎨 تغییر فونت اعداد زمان\n\n"
            "لطفاً فونت مورد نظر را انتخاب کنید:",
            reply_markup=get_font_keyboard(),
            parse_mode='Markdown'
        )
    elif selection_type == "bio":
        del context.user_data["selecting_channel"]
        del context.user_data["selection_type"]
        
        channel_data = user_channels[user_id][selected_channel_id]
        context.user_data["awaiting_bio_text"] = True
        
        await update.message.reply_text(
            f"📝 تنظیم بیوگرافی برای {channel_data['base_name']}\n\n"
            f"لطفاً متن بیوگرافی را ارسال کنید:\n\n"
            f"📌 مثال:\n"
            f"`بهترین کانال آموزشی`\n"
            f"`گروه دوستان و خانواده`\n\n"
            f"💡 زمان به صورت خودکار به انتهای بیوگرافی اضافه می‌شود\n"
            f"❌ برای غیرفعال کردن بیوگرافی: `غیرفعال`\n"
            f"❌ برای لغو: /cancel",
            parse_mode='Markdown'
        )

async def handle_time_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    user_id = update.effective_user.id
    channel_id = context.user_data["selected_channel_id"]
    
    if "فعال کردن زمان در نام" in message_text:
        user_channels[user_id][channel_id]["use_name_time"] = True
    elif "غیرفعال کردن زمان در نام" in message_text:
        user_channels[user_id][channel_id]["use_name_time"] = False
    elif "فعال کردن زمان در بیوگرافی" in message_text:
        user_channels[user_id][channel_id]["use_bio_time"] = True
    elif "غیرفعال کردن زمان در بیوگرافی" in message_text:
        user_channels[user_id][channel_id]["use_bio_time"] = False
    
    save_data()
    
    channel_name = user_channels[user_id][channel_id]["base_name"]
    use_name = user_channels[user_id][channel_id]["use_name_time"]
    use_bio = user_channels[user_id][channel_id]["use_bio_time"]
    
    await update.message.reply_text(
        f"✅ تنظیمات زمان برای {channel_name} به‌روز شد!\n\n"
        f"🎯 نمایش زمان در نام: {'فعال ✅' if use_name else 'غیرفعال ❌'}\n"
        f"📝 نمایش زمان در بیوگرافی: {'فعال ✅' if use_bio else 'غیرفعال ❌'}\n\n"
        f"تغییرات از همین لحظه اعمال می‌شوند",
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )
    
    del context.user_data["selected_channel_id"]

async def handle_bio_text(update: Update, context: ContextTypes.DEFAULT_TYPE, bio_text: str):
    user_id = update.effective_user.id
    channel_id = context.user_data["selected_channel_id"]
    
    if bio_text.lower() == "غیرفعال":
        user_channels[user_id][channel_id]["use_bio_time"] = False
        user_channels[user_id][channel_id]["bio_text"] = ""
        save_data()
        
        try:
            await context.bot.set_chat_description(
                chat_id=int(channel_id), 
                description=""
            )
        except Exception as e:
            logger.warning(f"خطا در پاک کردن بیوگرافی: {e}")
        
        await update.message.reply_text(
            "✅ نمایش زمان در بیوگرافی غیرفعال شد.",
            reply_markup=get_main_keyboard(user_id)
        )
    else:
        user_channels[user_id][channel_id]["bio_text"] = bio_text
        save_data()
        
        await update.message.reply_text(
            f"✅ بیوگرافی با موفقیت تنظیم شد!\n\n"
            f"📝 متن بیوگرافی: {bio_text}\n"
            f"⏰ زمان به صورت خودکار به انتهای بیوگرافی اضافه می‌شود",
            reply_markup=get_main_keyboard(user_id)
        )
    
    del context.user_data["selected_channel_id"]
    del context.user_data["awaiting_bio_text"]

async def handle_font_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    font_style = None
    for font_name in FONT_STYLES.keys():
        if font_name in message_text:
            font_style = font_name
            break
    
    if not font_style:
        await update.message.reply_text(
            "❌ فونت انتخاب شده نامعتبر است!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    if "selected_channel_id" in context.user_data:
        channel_id = context.user_data["selected_channel_id"]
        user_channels[user_id][channel_id]["font_style"] = font_style
        channel_name = user_channels[user_id][channel_id]["base_name"]
        del context.user_data["selected_channel_id"]
        
        await update.message.reply_text(
            f"✅ فونت اعداد برای {channel_name} با موفقیت تغییر کرد!\n\n"
            f"🎨 فونت جدید: {font_style}\n"
            f"🕒 نمونه زمان: {convert_to_font('12:34', font_style)}\n\n"
            f"✅ تغییرات بر روی نام و بیوگرافی کانال اعمال شد",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )
    else:
        if user_id in user_channels:
            for channel_id in user_channels[user_id]:
                user_channels[user_id][channel_id]["font_style"] = font_style
            save_data()
        
        sample_time = convert_to_font("12:34", font_style)
        
        await update.message.reply_text(
            f"✅ فونت اعداد با موفقیت تغییر کرد!\n\n"
            f"🎨 فونت جدید: {font_style}\n"
            f"🕒 نمونه زمان: {sample_time}\n\n"
            f"✅ تغییرات بر روی تمام کانال‌های شما اعمال شد",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='Markdown'
        )

async def points_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    points = user_points.get(user_id, 0)
    
    await update.message.reply_text(
        f"🎁 سیستم امتیازدهی\n\n"
        f"🏆 امتیاز شما: {points} امتیاز\n\n"
        f"💰 روش‌های کسب امتیاز:\n"
        f"• 📨 هر رفرال موفق: {REFERRAL_POINTS} امتیاز\n"
        f"• 👥 معرفی دوستان: {REFERRAL_POINTS} امتیاز\n\n"
        f"💎 هزینه‌ها:\n"
        f"• ثبت هر کانال/گروه: {channel_points} امتیاز\n\n"
        f"📊 برای دریافت لینک رفرال خود از منوی اصلی استفاده کنید",
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    code = next((k for k, v in referral_codes.items() if v == user_id), None)
    
    if not code:
        code = generate_referral_code(user_id)
    
    referral_link = f"https://t.me/{context.bot.username}?start={code}"
    points = user_points.get(user_id, 0)
    
    await update.message.reply_text(
        f"📊 لینک رفرال شما\n\n"
        f"🔗 لینک اختصاصی:\n"
        f"`{referral_link}`\n\n"
        f"💰 مزایا:\n"
        f"• شما {REFERRAL_POINTS} امتیاز دریافت می‌کنید\n"
        f"• دوست شما هم {REFERRAL_POINTS} امتیاز می‌گیرد\n"
        f"• بدون محدودیت تعداد\n\n"
        f"🏆 امتیاز کل شما: {points}\n\n"
        f"📨 این لینک را برای دوستان خود ارسال کنید",
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    points = user_points.get(user_id, 0)
    channels_count = len(user_channels.get(user_id, {}))
    
    await update.message.reply_text(
        f"📈 آمار کاربری شما\n\n"
        f"👤 شناسه کاربری: `{user_id}`\n"
        f"🏆 امتیاز کل: {points} امتیاز\n"
        f"📊 کانال‌های فعال: {channels_count} عدد\n"
        f"💎 امتیاز مورد نیاز برای ثبت: {channel_points} امتیاز\n\n"
        f"📅 تاریخ عضویت: {datetime.now().strftime('%Y/%m/%d')}",
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    help_text = """
📖 راهنمای استفاده از ربات

🤖 توضیحات کلی:
این ربات برای نمایش زمان زنده در نام و بیوگرافی کانال‌ها و گروه‌های شما طراحی شده است.

🛠 امکانات اصلی:
• ⏰ نمایش زمان به وقت تهران در نام کانال/گروه
• 📝 نمایش زمان به وقت تهران در بیوگرافی
• 🎨 پشتیبانی از ۵ فونت مختلف
• 🏆 سیستم امتیازدهی هوشمند
• 📊 لینک رفرال اختصاصی
• 👥 مدیریت چندین کانال

📋 مراحل استفاده:
1. ابتدا امتیاز کافی جمع‌آوری کنید
2. کانال/گروه خود را ثبت کنید
3. فونت مورد نظر را انتخاب کنید
4. بیوگرافی را تنظیم کنید
5. از نمایش زمان لذت ببرید!

❓ پرسش‌های متداول:
• هر کانال ۱۰ امتیاز هزینه دارد
• هر رفرال موفق ۵ امتیاز می‌دهد
• زمان هر ۵ ثانیه آپدیت می‌شود
• می‌توانید برای هر کانال فونت جداگانه تنظیم کنید

💎 کسب امتیاز:
فقط از طریق سیستم رفرال می‌توانید امتیاز کسب کنید

📞 پشتیبانی: @KralSupport
    """
    
    await update.message.reply_text(
        help_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text(
            "❌ شما دسترسی ادمین ندارید!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    await update.message.reply_text(
        "🛠 پنل مدیریت\n\n"
        "به پنل مدیریت خوش آمدید. لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    total_users = len(user_channels)
    total_channels = sum(len(channels) for channels in user_channels.values())
    total_banned = len(banned_users)
    total_points = sum(user_points.values()) if user_points else 0
    total_used_referrals = len(used_referrals)
    total_referral_codes = len(referral_codes)
    
    await update.message.reply_text(
        f"📊 آمار کامل ربات\n\n"
        f"👤 کاربران فعال: {total_users}\n"
        f"📌 کانال‌ها/گروه‌ها: {total_channels}\n"
        f"🚫 کاربران بن شده: {total_banned}\n"
        f"🏆 مجموع امتیازها: {total_points}\n"
        f"⭐ امتیاز هر کانال: {channel_points}\n"
        f"🔗 کدهای رفرال: {total_referral_codes}\n"
        f"📩 رفرال‌های استفاده شده: {total_used_referrals}\n"
        f"💰 امتیاز هر رفرال: {REFERRAL_POINTS}",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def ban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    await update.message.reply_text(
        "🚫 بن کاربر\n\nلطفاً آیدی عددی کاربر را برای بن کردن ارسال کنید:",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data["awaiting_ban"] = True

async def handle_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_str: str):
    if update.effective_chat.type != "private":
        return
    admin_id = update.effective_user.id
    
    try:
        user_id = int(user_id_str.strip())
        banned_users.add(user_id)
        save_data()
        await update.message.reply_text(
            f"✅ کاربر {user_id} با موفقیت بن شد.",
            reply_markup=get_admin_keyboard()
        )
    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً یک آیدی عددی معتبر وارد کنید.",
            reply_markup=get_admin_keyboard()
        )
    finally:
        del context.user_data["awaiting_ban"]

async def unban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    await update.message.reply_text(
        "✅ آنبن کاربر\n\nلطفاً آیدی عددی کاربر را برای آنبن کردن ارسال کنید:",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data["awaiting_unban"] = True

async def handle_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_str: str):
    if update.effective_chat.type != "private":
        return
    admin_id = update.effective_user.id
    
    try:
        user_id = int(user_id_str.strip())
        if user_id in banned_users:
            banned_users.remove(user_id)
            save_data()
            await update.message.reply_text(
                f"✅ کاربر {user_id} با موفقیت آنبن شد.",
                reply_markup=get_admin_keyboard()
            )
        else:
            await update.message.reply_text(
                "ℹ️ این کاربر بن نشده بود.",
                reply_markup=get_admin_keyboard()
            )
    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً یک آیدی عددی معتبر وارد کنید.",
            reply_markup=get_admin_keyboard()
        )
    finally:
        del context.user_data["awaiting_unban"]

async def channel_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not user_channels:
        await update.message.reply_text(
            "📭 هنوز هیچ کانال/گروهی ثبت نشده است.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    message = "📋 لیست کانال‌ها/گروه‌های ثبت شده:\n\n"
    for user_id, channels in user_channels.items():
        message += f"👤 کاربر {user_id} (امتیاز: {user_points.get(user_id, 0)}):\n"
        for channel_id, data in channels.items():
            message += f"  - {data['base_name']} (ID: {channel_id})\n"
    
    await update.message.reply_text(
        message[:4000],
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def manage_points_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    await update.message.reply_text(
        "🎯 مدیریت امتیازها\n\n"
        "لطفاً آیدی کاربر و مقدار امتیاز را به صورت زیر ارسال کنید:\n\n"
        "📌 فرمت:\n"
        "`123456789 +10` (برای اضافه کردن)\n"
        "`123456789 -5` (برای کم کردن)\n\n"
        "❌ برای لغو: /cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data["awaiting_points"] = True

async def handle_points_management(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    if update.effective_chat.type != "private":
        return
    admin_id = update.effective_user.id
    
    try:
        parts = message_text.split()
        user_id = int(parts[0])
        points_change = int(parts[1])
        
        current_points = user_points.get(user_id, 0)
        new_points = current_points + points_change
        user_points[user_id] = new_points
        save_data()
        
        await update.message.reply_text(
            f"✅ امتیاز کاربر {user_id} با موفقیت تغییر کرد.\n"
            f"امتیاز جدید: {new_points}",
            reply_markup=get_admin_keyboard()
        )
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ فرمت پیام نادرست است!",
            reply_markup=get_admin_keyboard()
        )
    finally:
        del context.user_data["awaiting_points"]

async def set_channel_points_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    await update.message.reply_text(
        f"⚙️ تنظیم امتیاز کانال/گروه\n\n"
        f"امتیاز فعلی برای هر کانال/گروه: {channel_points}\n\n"
        f"لطفاً مقدار جدید امتیاز را ارسال کنید:",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data["awaiting_channel_points"] = True

async def handle_channel_points(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    if update.effective_chat.type != "private":
        return
    admin_id = update.effective_user.id
    
    try:
        global channel_points
        channel_points = int(message_text)
        save_data()
        
        await update.message.reply_text(
            f"✅ امتیاز هر کانال/گروه با موفقیت به {channel_points} تغییر کرد.",
            reply_markup=get_admin_keyboard()
        )
    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً یک عدد معتبر وارد کنید!",
            reply_markup=get_admin_keyboard()
        )
    finally:
        del context.user_data["awaiting_channel_points"]

async def update_channel_loop(bot, channel_id, user_id):
    task_key = f"{user_id}_{channel_id}"
    
    while True:
        try:
            if user_id not in user_channels or channel_id not in user_channels[user_id]:
                logger.info(f"کانال {channel_id} حذف شده است. توقف آپدیت.")
                break
            
            channel_data = user_channels[user_id][channel_id]
            base_name = channel_data["base_name"]
            font_style = channel_data["font_style"]
            use_name_time = channel_data.get("use_name_time", True)
            use_bio_time = channel_data.get("use_bio_time", False)
            
            tehran_time = datetime.now(pytz.timezone('Asia/Tehran'))
            current_time = tehran_time.strftime("%H:%M")
            formatted_time = convert_to_font(current_time, font_style)
            
            if use_name_time:
                new_name = f"{base_name} | {formatted_time}"
                try:
                    await bot.set_chat_title(chat_id=int(channel_id), title=new_name)
                except Exception as e:
                    logger.error(f"خطا در آپدیت نام کانال {channel_id}: {e}")
            
            if use_bio_time:
                bio_text = channel_data.get("bio_text", "")
                if bio_text:
                    bio_with_time = f"{bio_text} | {formatted_time}"
                else:
                    bio_with_time = formatted_time
                
                try:
                    await bot.set_chat_description(chat_id=int(channel_id), description=bio_with_time)
                except Exception as e:
                    logger.error(f"خطا در آپدیت بیوگرافی کانال {channel_id}: {e}")
            elif channel_data.get("bio_text"):
                try:
                    await bot.set_chat_description(chat_id=int(channel_id), description=channel_data['bio_text'])
                except Exception as e:
                    logger.error(f"خطا در آپدیت بیوگرافی ساده کانال {channel_id}: {e}")
                
            await asyncio.sleep(5)
            
        except asyncio.CancelledError:
            logger.info(f"تسک آپدیت برای کانال {channel_id} لغو شد")
            break
        except Exception as e:
            logger.error(f"خطا در آپدیت کانال/گروه {channel_id}: {e}")
            await asyncio.sleep(10)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    for key in list(context.user_data.keys()):
        if key.startswith("awaiting_") or key.startswith("selecting_"):
            del context.user_data[key]
    
    await update.message.reply_text(
        "✅ عملیات لغو شد.",
        reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END

async def delete_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post or (update.message and update.message.chat.type in ['group', 'supergroup', 'channel']):
        message = update.channel_post or update.message
        
        if (message.new_chat_title or 
            message.new_chat_photo or 
            message.delete_chat_photo or
            getattr(message, 'left_chat_member', None) or
            getattr(message, 'new_chat_members', None) or
            getattr(message, 'pinned_message', None)):
            
            try:
                await message.delete()
                logger.info(f"پیام سرویسی در چت {message.chat.id} حذف شد")
            except Exception as e:
                logger.error(f"خطا در حذف پیام سرویسی: {e}")

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start, filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("cancel", cancel, filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("help", show_help, filters.ChatType.PRIVATE))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
        handle_message
    ))
    
    application.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP,
            delete_service_messages
        ),
        group=1
    )
    
    print("ربات در حال راه‌اندازی...")
    application.run_polling()

if __name__ == "__main__":
    main()