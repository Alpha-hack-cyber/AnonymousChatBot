# main.py
# ربات چت ناشناس دوطرفه با سیستم شناسایی پیشرفته

import telebot
from telebot import types
import sqlite3
import logging
import os
import time
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = "8560780748:AAF10ufPJTx2vsInE1gy3OCFPXBwIRgw-nc"
OWNER_ID = 8477273540

DB_FILE = 'anon_chat_advanced.db'

def init_db():
    """ایجاد دیتابیس با ساختار پیشرفته"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # جدول کاربران با شناسه یکتا
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            user_hash TEXT UNIQUE,
            display_name TEXT,
            joined_at TEXT
        )
    ''')
    
    # جدول نگاشت پیام‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_map (
            message_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            owner_message_id INTEGER,
            is_from_owner BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logging.info("Database initialized successfully")

def generate_user_hash(user_id, username, first_name):
    """تولید هش یکتا برای شناسایی کاربر"""
    import datetime
    # ترکیب اطلاعات کاربر با زمان فعلی برای ایجاد هش یکتا
    data = f"{user_id}_{username}_{first_name}_{datetime.datetime.now().timestamp()}"
    hash_obj = hashlib.md5(data.encode())
    short_hash = hash_obj.hexdigest()[:8].upper()
    return short_hash

def add_user(user_id, username=None, first_name=None):
    """اضافه کردن کاربر جدید"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # بررسی وجود کاربر
    cursor.execute('SELECT user_hash, display_name FROM users WHERE user_id = ?', (user_id,))
    existing = cursor.fetchone()
    
    if not existing:
        # تولید هش جدید
        user_hash = generate_user_hash(user_id, username, first_name)
        
        # ایجاد نام نمایشی
        if username:
            display_name = f"@{username}"
        elif first_name:
            display_name = first_name
        else:
            display_name = f"User_{user_hash}"
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, user_hash, display_name, joined_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (user_id, username, first_name, user_hash, display_name))
    else:
        user_hash, display_name = existing
    
    conn.commit()
    conn.close()
    return user_hash, display_name

def get_user_display_info(user_id):
    """دریافت اطلاعات نمایشی کاربر"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT display_name, user_hash FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        display_name, user_hash = result
        return {
            'display_name': display_name,
            'user_hash': user_hash,
            'short_id': f"ID:{str(user_id)[:4]}"
        }
    return None

def get_user_count():
    """تعداد کاربران"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def save_mapping(message_id, user_id, owner_message_id=None, is_from_owner=False):
    """ذخیره نگاشت پیام"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO message_map (message_id, user_id, owner_message_id, is_from_owner)
        VALUES (?, ?, ?, ?)
    ''', (message_id, user_id, owner_message_id, is_from_owner))
    conn.commit()
    conn.close()

def get_user_id_from_mapping(message_id):
    """دریافت user_id از message_id"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM message_map WHERE message_id = ?', (message_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_owner_message_id(user_id, message_id):
    """دریافت owner_message_id مربوطه"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message_id FROM message_map 
        WHERE user_id = ? AND owner_message_id = ? AND is_from_owner = 0
    ''', (user_id, message_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

bot = telebot.TeleBot(TOKEN)

# ایجاد دیتابیس اگر وجود ندارد
if not os.path.exists(DB_FILE):
    init_db()
    print("✅ Nᴇᴡ ᴅᴀᴛᴀʙᴀsᴇ ᴄʀᴇᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ")

# ── فونت زیبا برای همه متن‌ها و دکمه‌ها ──
def get_main_menu(is_owner=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("✨ sᴛᴀʀᴛ ᴄʜᴀᴛ ✉️"))
    markup.add(types.KeyboardButton("❓ ʜᴇʟᴘ 💭"))
    markup.add(types.KeyboardButton("ℹ️ ᴀʙᴏᴜᴛ ᴍᴇ"))
    if is_owner:
        markup.add(types.KeyboardButton("📊 sᴛᴀᴛs"))
        markup.add(types.KeyboardButton("📢 ʙʀᴏᴀᴅᴄᴀsᴛ"))
    return markup

# لیست دکمه‌های منو
MENU_BUTTONS = [
    "✨ sᴛᴀʀᴛ ᴄʜᴀᴛ ✉️",
    "❓ ʜᴇʟᴘ 💭",
    "ℹ️ ᴀʙᴏᴜᴛ ᴍᴇ",
    "📊 sᴛᴀᴛs",
    "📢 ʙʀᴏᴀᴅᴄᴀsᴛ"
]

WELCOME_USER = """
🌌 Wᴇʟᴄᴏᴍᴇ ᴛᴏ ᴀɴᴏɴʏᴍᴏᴜs ᴄʜᴀᴛ! ✨

Yᴏᴜ ᴄᴀɴ sᴇɴᴅ ᴀɴʏᴛʜɪɴɢ — ᴛᴇxᴛ, ᴘʜᴏᴛᴏ, ᴠɪᴅᴇᴏ, ᴀᴜᴅɪᴏ, sᴛɪᴄᴋᴇʀ, ɢɪғ...

✨ Fᴇᴀᴛᴜʀᴇs:
• Cᴏᴍᴘʟᴇᴛᴇʟʏ ᴀɴᴏɴʏᴍᴏᴜs
• Tᴡᴏ-ᴡᴀʏ ᴄʜᴀᴛ
• Rᴇᴘʟʏ ᴛᴏ ᴏᴡɴᴇʀ's ᴍᴇssᴀɢᴇs

Iᴛ ᴡɪʟʟ ʙᴇ sᴇɴᴛ ᴀɴᴏɴʏᴍᴏᴜsʟʏ ᴛᴏ ᴛʜᴇ ᴏᴡɴᴇʀ. 🔒
"""
WELCOME_OWNER = """
👑 Hᴇʟʟᴏ ᴏᴡɴᴇʀ! 🌟
Yᴏᴜʀ ᴀɴᴏɴʏᴍᴏᴜs ᴄʜᴀᴛ ʙᴏᴛ ɪs ʀᴇᴀᴅʏ.

✨ Fᴇᴀᴛᴜʀᴇs:
• Rᴇᴄᴇɪᴠᴇ ᴀɴᴏɴʏᴍᴏᴜs ᴍᴇssᴀɢᴇs
• Sᴇᴇ ᴜsᴇʀ's ᴅɪsᴘʟᴀʏ ɴᴀᴍᴇ
• Rᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇssᴀɢᴇ
• Usᴇʀs ᴄᴀɴ ʀᴇᴘʟʏ ʙᴀᴄᴋ

Wᴀɪᴛɪɴɢ ғᴏʀ ᴍᴇssᴀɢᴇs... 📩
"""

# ── هندل دکمه‌های منو ──
@bot.message_handler(func=lambda m: m.text in MENU_BUTTONS)
def handle_menu(message):
    user_id = message.from_user.id
    text = message.text

    if text == "✨ sᴛᴀʀᴛ ᴄʜᴀᴛ ✉️":
        bot.reply_to(message, "Wʀɪᴛᴇ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ (ᴛᴇxᴛ, ᴘʜᴏᴛᴏ, ᴠɪᴅᴇᴏ, sᴛɪᴄᴋᴇʀ, ɢɪғ...)", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_user_message)

    elif text == "❓ ʜᴇʟᴘ 💭":
        help_text = """
🌟 Hᴇʟᴘ & Gᴜɪᴅᴇ

Fᴏʀ ᴜsᴇʀs:
• Sᴇɴᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ (ᴛᴇxᴛ, ᴘʜᴏᴛᴏ, ᴠɪᴅᴇᴏ, ᴀᴜᴅɪᴏ, ғɪʟᴇ, sᴛɪᴄᴋᴇʀ, ɢɪғ)
• Iᴛ ɢᴏᴇs ᴀɴᴏɴʏᴍᴏᴜsʟʏ ᴛᴏ ᴛʜᴇ ᴏᴡɴᴇʀ
• Rᴇᴘʟʏ ᴛᴏ ᴏᴡɴᴇʀ's ᴍᴇssᴀɢᴇs ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ

Fᴏʀ ᴏᴡɴᴇʀ:
• Rᴇᴄᴇɪᴠᴇ ᴀɴᴏɴʏᴍᴏᴜs ᴍᴇssᴀɢᴇs ᴡɪᴛʜ ᴜsᴇʀ's ᴅɪsᴘʟᴀʏ ɴᴀᴍᴇ
• Rᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇssᴀɢᴇ ᴛᴏ ʀᴇsᴘᴏɴᴅ
• Usᴇ ᴜsᴇʀ ɪɴғᴏ ʙᴜᴛᴛᴏɴ ғᴏʀ ᴅᴇᴛᴀɪʟs

Pʀɪᴠᴀᴄʏ ғɪʀsᴛ 🔒 • Tᴡᴏ-ᴡᴀʏ ᴄʜᴀᴛ ✨
"""
        bot.reply_to(message, help_text, reply_markup=get_main_menu(user_id == OWNER_ID), parse_mode='Markdown')

    elif text == "ℹ️ ᴀʙᴏᴜᴛ ᴍᴇ":
        bot.reply_to(message, "Aɴᴏɴʏᴍᴏᴜs Cʜᴀᴛ Bᴏᴛ v3.0\nAᴅᴠᴀɴᴄᴇᴅ ᴜsᴇʀ ɪᴅᴇɴᴛɪғɪᴄᴀᴛɪᴏɴ\nMᴀᴅᴇ ᴡɪᴛʜ ❤️\nVᴇʀsɪᴏɴ 2025", 
                     reply_markup=get_main_menu(user_id == OWNER_ID))

    elif text == "📊 sᴛᴀᴛs" and user_id == OWNER_ID:
        count = get_user_count()
        
        stats_text = f"""
📊 Sᴛᴀᴛɪsᴛɪᴄs

👥 Tᴏᴛᴀʟ ᴜɴɪǫᴜᴇ ᴜsᴇʀs: {count}

Yᴏᴜʀ ᴀɴᴏɴʏᴍᴏᴜs ᴄʜᴀᴛ ɪs ɢʀᴏᴡɪɴɢ! 🌟
"""
        bot.reply_to(message, stats_text, reply_markup=get_main_menu(True), parse_mode='Markdown')

    elif text == "📢 ʙʀᴏᴀᴅᴄᴀsᴛ" and user_id == OWNER_ID:
        bot.reply_to(message, "Nᴏᴡ sᴇɴᴅ ᴛʜᴇ ᴍᴇssᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ᴛᴏ ᴀʟʟ ᴜsᴇʀs.\n\nIᴛ ᴡɪʟʟ ʙᴇ sᴇɴᴛ ᴛᴏ ᴇᴠᴇʀʏᴏɴᴇ ᴡʜᴏ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.")
        bot.register_next_step_handler(message, broadcast_message)

# ── پردازش پیام کاربر ──
def process_user_message(message):
    """پردازش پیام کاربر و ارسال آن به صاحب ربات"""
    user_id = message.from_user.id
    
    # اگر کاربر دکمه‌ای از منو را زد
    if message.text in MENU_BUTTONS:
        handle_menu(message)
        return
    
    # دریافت یا ایجاد اطلاعات کاربر
    user_info = get_user_display_info(user_id)
    if not user_info:
        user_hash, display_name = add_user(user_id, message.from_user.username, message.from_user.first_name)
        user_info = get_user_display_info(user_id)
    
    display_name = user_info['display_name']
    user_hash = user_info['user_hash']
    short_id = user_info['short_id']
    
    try:
        # ارسال پیام به صاحب ربات
        if message.text:
            caption = f"📩 Nᴇᴡ ᴀɴᴏɴʏᴍᴏᴜs ᴍᴇssᴀɢᴇ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Mᴇssᴀɢᴇ:\n{message.text}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_message(OWNER_ID, caption, reply_markup=markup, parse_mode='Markdown')
            
        elif message.photo:
            caption = f"📩 Nᴇᴡ ᴀɴᴏɴʏᴍᴏᴜs ᴍᴇssᴀɢᴇ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Mᴇssᴀɢᴇ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_photo(OWNER_ID, message.photo[-1].file_id, caption=caption, reply_markup=markup, parse_mode='Markdown')
            
        elif message.video:
            caption = f"📩 Nᴇᴡ ᴀɴᴏɴʏᴍᴏᴜs ᴍᴇssᴀɢᴇ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Mᴇssᴀɢᴇ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_video(OWNER_ID, message.video.file_id, caption=caption, reply_markup=markup, parse_mode='Markdown')
            
        elif message.audio:
            caption = f"📩 Nᴇᴡ ᴀɴᴏɴʏᴍᴏᴜs ᴍᴇssᴀɢᴇ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Mᴇssᴀɢᴇ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_audio(OWNER_ID, message.audio.file_id, caption=caption, reply_markup=markup, parse_mode='Markdown')
            
        elif message.document:
            caption = f"📩 Nᴇᴡ ᴀɴᴏɴʏᴍᴏᴜs ᴍᴇssᴀɢᴇ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Mᴇssᴀɢᴇ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_document(OWNER_ID, message.document.file_id, caption=caption, reply_markup=markup, parse_mode='Markdown')
            
        elif message.sticker:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_sticker(OWNER_ID, message.sticker.file_id)
            bot.send_message(OWNER_ID, f"📩 Nᴇᴡ ᴀɴᴏɴʏᴍᴏᴜs sᴛɪᴄᴋᴇʀ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`", 
                             reply_markup=markup, parse_mode='Markdown')
            
        elif message.voice:
            caption = f"📩 Nᴇᴡ ᴀɴᴏɴʏᴍᴏᴜs ᴍᴇssᴀɢᴇ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Mᴇssᴀɢᴇ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_voice(OWNER_ID, message.voice.file_id, caption=caption, reply_markup=markup, parse_mode='Markdown')
            
        elif message.video_note:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_video_note(OWNER_ID, message.video_note.file_id)
            bot.send_message(OWNER_ID, f"📩 Nᴇᴡ ᴀɴᴏɴʏᴍᴏᴜs ᴠɪᴅᴇᴏ ɴᴏᴛᴇ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`", 
                             reply_markup=markup, parse_mode='Markdown')
        
        else:
            bot.reply_to(message, "Tʜɪs ᴍᴇssᴀɢᴇ ᴛʏᴘᴇ ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ.")
            return
        
        # ذخیره مپینگ پیام
        if 'sent_msg' in locals():
            save_mapping(sent_msg.message_id, user_id, None, False)
            logging.info(f"Anonymous message sent from user {user_id} (Display: {display_name})")
        
        # پاسخ به کاربر
        bot.reply_to(message, f"✅ Yᴏᴜʀ ᴍᴇssᴀɢᴇ ʜᴀs ʙᴇᴇɴ sᴇɴᴛ ᴀɴᴏɴʏᴍᴏᴜsʟʏ!\n\n👤 Yᴏᴜʀ ɪᴅᴇɴᴛɪғɪᴄᴀᴛɪᴏɴ: {display_name}\n💡 Nᴏᴡ ʏᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴏᴡɴᴇʀ's ᴍᴇssᴀɢᴇs ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ. ✨", 
                     reply_markup=get_main_menu(user_id == OWNER_ID), parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Error sending anonymous message: {e}")
        bot.reply_to(message, "❌ Sᴏʀʀʏ, ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.", 
                     reply_markup=get_main_menu(user_id == OWNER_ID))

# ── پردازش پاسخ صاحب ربات ──
@bot.message_handler(content_types=['text', 'photo', 'video', 'audio', 'document', 'sticker', 'voice', 'video_note'], 
                     func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message)
def handle_owner_reply(message):
    """پردازش ریپلای صاحب ربات"""
    if not message.reply_to_message:
        return
    
    target_user = get_user_id_from_mapping(message.reply_to_message.message_id)
    if not target_user:
        bot.reply_to(message, "❌ Uɴᴀʙʟᴇ ᴛᴏ ғɪɴᴅ ᴛʜᴇ ᴜsᴇʀ.")
        return
    
    user_info = get_user_display_info(target_user)
    if not user_info:
        bot.reply_to(message, "❌ Usᴇʀ ɪɴғᴏ ɴᴏᴛ ғᴏᴜɴᴅ.")
        return
    
    display_name = user_info['display_name']
    
    try:
        if message.text:
            sent_msg = bot.send_message(target_user, f"✨ Rᴇᴘʟʏ ғʀᴏᴍ ᴏᴡɴᴇʀ:\n\n{message.text}\n\n💡 Yᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ.", 
                                         parse_mode='Markdown')
        elif message.photo:
            sent_msg = bot.send_photo(target_user, message.photo[-1].file_id, 
                                       caption=f"✨ Rᴇᴘʟʏ ғʀᴏᴍ ᴏᴡɴᴇʀ (ᴘʜᴏᴛᴏ)\n\n💡 Yᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ.", 
                                       parse_mode='Markdown')
        elif message.video:
            sent_msg = bot.send_video(target_user, message.video.file_id, 
                                       caption=f"✨ Rᴇᴘʟʏ ғʀᴏᴍ ᴏᴡɴᴇʀ (ᴠɪᴅᴇᴏ)\n\n💡 Yᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ.", 
                                       parse_mode='Markdown')
        elif message.audio:
            sent_msg = bot.send_audio(target_user, message.audio.file_id, 
                                       caption=f"✨ Rᴇᴘʟʏ ғʀᴏᴍ ᴏᴡɴᴇʀ (ᴀᴜᴅɪᴏ)\n\n💡 Yᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ.", 
                                       parse_mode='Markdown')
        elif message.document:
            sent_msg = bot.send_document(target_user, message.document.file_id, 
                                          caption=f"✨ Rᴇᴘʟʏ ғʀᴏᴍ ᴏᴡɴᴇʀ (ᴅᴏᴄᴜᴍᴇɴᴛ)\n\n💡 Yᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ.", 
                                          parse_mode='Markdown')
        elif message.sticker:
            bot.send_sticker(target_user, message.sticker.file_id)
            sent_msg = bot.send_message(target_user, f"✨ Rᴇᴘʟʏ ғʀᴏᴍ ᴏᴡɴᴇʀ (sᴛɪᴄᴋᴇʀ)\n\n💡 Yᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ.", 
                                         parse_mode='Markdown')
        elif message.voice:
            sent_msg = bot.send_voice(target_user, message.voice.file_id, 
                                       caption=f"✨ Rᴇᴘʟʏ ғʀᴏᴍ ᴏᴡɴᴇʀ (ᴠᴏɪᴄᴇ)\n\n💡 Yᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ.", 
                                       parse_mode='Markdown')
        elif message.video_note:
            bot.send_video_note(target_user, message.video_note.file_id)
            sent_msg = bot.send_message(target_user, f"✨ Rᴇᴘʟʏ ғʀᴏᴍ ᴏᴡɴᴇʀ (ᴠɪᴅᴇᴏ ɴᴏᴛᴇ)\n\n💡 Yᴏᴜ ᴄᴀɴ ʀᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴛʜᴇ ᴄʜᴀᴛ.", 
                                         parse_mode='Markdown')
        
        # ذخیره مپینگ پیام صاحب ربات
        if 'sent_msg' in locals():
            save_mapping(sent_msg.message_id, target_user, message.message_id, True)
        
        bot.reply_to(message, f"✅ Rᴇᴘʟʏ sᴇɴᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!\n👤 Usᴇʀ: {display_name}\n💬 Tʜᴇ ᴜsᴇʀ ᴄᴀɴ ɴᴏᴡ ʀᴇᴘʟʏ ᴛᴏ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.", 
                     parse_mode='Markdown')
        logging.info(f"Owner replied to user {target_user} (Display: {display_name})")
        
    except Exception as e:
        logging.error(f"Error sending reply: {e}")
        bot.reply_to(message, f"❌ Eʀʀᴏʀ sᴇɴᴅɪɴɢ ʀᴇᴘʟʏ: {str(e)}")

# ── پردازش پاسخ کاربر به پیام صاحب ربات ──
@bot.message_handler(content_types=['text', 'photo', 'video', 'audio', 'document', 'sticker', 'voice', 'video_note'], 
                     func=lambda m: m.from_user.id != OWNER_ID and m.reply_to_message)
def handle_user_reply_to_owner(message):
    """پردازش ریپلای کاربر به پیام صاحب ربات"""
    if not message.reply_to_message:
        return
    
    user_id = message.from_user.id
    user_info = get_user_display_info(user_id)
    
    if not user_info:
        user_hash, display_name = add_user(user_id, message.from_user.username, message.from_user.first_name)
        user_info = get_user_display_info(user_id)
    
    display_name = user_info['display_name']
    user_hash = user_info['user_hash']
    short_id = user_info['short_id']
    
    # بررسی آیا این پیام ریپلای به پیام صاحب ربات است
    owner_message_id = get_owner_message_id(user_id, message.reply_to_message.message_id)
    
    if not owner_message_id:
        # اگر ریپلای به پیام صاحب ربات نیست، آن را به عنوان پیام جدید پردازش کن
        process_user_message(message)
        return
    
    try:
        # ارسال پاسخ کاربر به صاحب ربات
        if message.text:
            caption = f"💬 Usᴇʀ ʀᴇᴘʟɪᴇᴅ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Rᴇᴘʟʏ:\n{message.text}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_message(OWNER_ID, caption, reply_markup=markup, parse_mode='Markdown', 
                                         reply_to_message_id=owner_message_id)
            
        elif message.photo:
            caption = f"💬 Usᴇʀ ʀᴇᴘʟɪᴇᴅ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Rᴇᴘʟʏ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_photo(OWNER_ID, message.photo[-1].file_id, caption=caption, reply_markup=markup, 
                                       parse_mode='Markdown', reply_to_message_id=owner_message_id)
            
        elif message.video:
            caption = f"💬 Usᴇʀ ʀᴇᴘʟɪᴇᴅ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Rᴇᴘʟʏ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_video(OWNER_ID, message.video.file_id, caption=caption, reply_markup=markup, 
                                       parse_mode='Markdown', reply_to_message_id=owner_message_id)
            
        elif message.audio:
            caption = f"💬 Usᴇʀ ʀᴇᴘʟɪᴇᴅ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Rᴇᴘʟʏ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_audio(OWNER_ID, message.audio.file_id, caption=caption, reply_markup=markup, 
                                       parse_mode='Markdown', reply_to_message_id=owner_message_id)
            
        elif message.document:
            caption = f"💬 Usᴇʀ ʀᴇᴘʟɪᴇᴅ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Rᴇᴘʟʏ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_document(OWNER_ID, message.document.file_id, caption=caption, reply_markup=markup, 
                                          parse_mode='Markdown', reply_to_message_id=owner_message_id)
            
        elif message.sticker:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_sticker(OWNER_ID, message.sticker.file_id, reply_to_message_id=owner_message_id)
            bot.send_message(OWNER_ID, f"💬 Usᴇʀ ʀᴇᴘʟɪᴇᴅ (sᴛɪᴄᴋᴇʀ)\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`", 
                             reply_markup=markup, parse_mode='Markdown', reply_to_message_id=owner_message_id)
            
        elif message.voice:
            caption = f"💬 Usᴇʀ ʀᴇᴘʟɪᴇᴅ\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`\n\n💬 Rᴇᴘʟʏ:\n{message.caption or '(ɴᴏ ᴛᴇxᴛ)'}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_voice(OWNER_ID, message.voice.file_id, caption=caption, reply_markup=markup, 
                                       parse_mode='Markdown', reply_to_message_id=owner_message_id)
            
        elif message.video_note:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📝 ᴀɴsᴡᴇʀ", callback_data=f"ans_{user_id}"),
                types.InlineKeyboardButton("👁️ ᴜsᴇʀ ɪɴғᴏ", callback_data=f"info_{user_id}"),
                types.InlineKeyboardButton("🔑 sʜᴏᴡ ʜᴀsʜ", callback_data=f"hash_{user_id}")
            )
            sent_msg = bot.send_video_note(OWNER_ID, message.video_note.file_id, reply_to_message_id=owner_message_id)
            bot.send_message(OWNER_ID, f"💬 Usᴇʀ ʀᴇᴘʟɪᴇᴅ (ᴠɪᴅᴇᴏ ɴᴏᴛᴇ)\n\n👤 Fʀᴏᴍ: {display_name}\n🔑 Hᴀsʜ: `{user_hash}`\n🆔 Sʜᴏʀᴛ ID: `{short_id}`", 
                             reply_markup=markup, parse_mode='Markdown', reply_to_message_id=owner_message_id)
        
        else:
            bot.reply_to(message, "Tʜɪs ᴍᴇssᴀɢᴇ ᴛʏᴘᴇ ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ.")
            return
        
        if 'sent_msg' in locals():
            save_mapping(sent_msg.message_id, user_id, None, False)
            logging.info(f"User {user_id} (Display: {display_name}) replied to owner")
        
        bot.reply_to(message, f"✅ Yᴏᴜʀ ʀᴇᴘʟʏ ʜᴀs ʙᴇᴇɴ sᴇɴᴛ!\n\n👤 Yᴏᴜʀ ɪᴅᴇɴᴛɪғɪᴄᴀᴛɪᴏɴ: {display_name}\n💡 Yᴏᴜ ᴄᴀɴ ᴄᴏɴᴛɪɴᴜᴇ ʀᴇᴘʟʏɪɴɢ ᴛᴏ ᴛʜᴇ ᴏᴡɴᴇʀ's ᴍᴇssᴀɢᴇs. ✨", 
                     reply_markup=get_main_menu(), parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Error sending user reply: {e}")
        bot.reply_to(message, "❌ Sᴏʀʀʏ, ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.", 
                     reply_markup=get_main_menu())

# ── پخش همگانی ──
def broadcast_message(message):
    if message.from_user.id != OWNER_ID:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()

    success = 0
    failed = 0

    for (user_id,) in users:
        try:
            if message.text:
                bot.send_message(user_id, message.text)
            elif message.photo:
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                bot.send_video(user_id, message.video.file_id, caption=message.caption)
            elif message.audio:
                bot.send_audio(user_id, message.audio.file_id, caption=message.caption)
            elif message.document:
                bot.send_document(user_id, message.document.file_id, caption=message.caption)
            success += 1
        except:
            failed += 1

    bot.reply_to(message, f"✅ Bʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!\nSᴜᴄᴄᴇss: {success}\nFᴀɪʟᴇᴅ: {failed}", 
                 reply_markup=get_main_menu(True))

# ── /start ──
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_hash, display_name = add_user(user_id, message.from_user.username, message.from_user.first_name)
    
    keyboard = get_main_menu(user_id == OWNER_ID)
    if user_id == OWNER_ID:
        bot.reply_to(message, WELCOME_OWNER, reply_markup=keyboard)
    else:
        bot.reply_to(message, WELCOME_USER, reply_markup=keyboard, parse_mode='Markdown')

# ── دکمه‌های شیشه‌ای ──
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split("_")
    if len(data) < 2:
        bot.answer_callback_query(call.id)
        return
    
    action = data[0]
    target_user_id = int(data[1])

    if action == "ans":
        bot.answer_callback_query(call.id, "📝 Rᴇᴘʟʏ ᴛᴏ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ sᴇɴᴅ ᴀ ʀᴇsᴘᴏɴsᴇ!")
        
    elif action == "info":
        try:
            user = bot.get_chat(target_user_id)
            user_info = get_user_display_info(target_user_id)
            
            if user_info:
                display_name = user_info['display_name']
                user_hash = user_info['user_hash']
                short_id = user_info['short_id']
            else:
                display_name = "Unknown"
                user_hash = "N/A"
                short_id = "N/A"
            
            username = user.username or "N/A"
            full_name = f"{user.first_name} {user.last_name or ''}".strip()
            
            text = f"""
┌──────────────────────┐
│    U S E R   I N F O    │
└──────────────────────┘

• Dɪsᴘʟᴀʏ Nᴀᴍᴇ: {display_name}
• Fᴜʟʟ Nᴀᴍᴇ: {full_name}
• Uꜱᴇʀɴᴀᴍᴇ: @{username}
• Uɴɪǫᴜᴇ Hᴀsʜ: `{user_hash}`
• Sʜᴏʀᴛ ID: `{short_id}`
• Fᴜʟʟ ID: `{target_user_id}`

• Dɪʀᴇᴄᴛ Lɪɴᴋ: tg://user?id={target_user_id}
"""
            bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Usᴇʀ ɪɴғᴏ sᴇɴᴛ!")
        except Exception as e:
            logging.error(f"Error fetching user info: {e}")
            bot.send_message(call.message.chat.id, "❌ Cᴏᴜʟᴅɴ'ᴛ ғᴇᴛᴄʜ ᴜsᴇʀ ɪɴғᴏ.")
            bot.answer_callback_query(call.id, "❌ Eʀʀᴏʀ!")
    
    elif action == "hash":
        user_info = get_user_display_info(target_user_id)
        if user_info:
            bot.answer_callback_query(call.id, f"🔑 Usᴇʀ Hᴀsʜ: {user_info['user_hash']}")
        else:
            bot.answer_callback_query(call.id, "❌ Hᴀsʜ ɴᴏᴛ ғᴏᴜɴᴅ!")

# اجرا
if __name__ == "__main__":
    print("✅ Aɴᴏɴʏᴍᴏᴜs Cʜᴀᴛ Bᴏᴛ v3.0 sᴛᴀʀᴛᴇᴅ... ✨")
    print(f"👑 Oᴡɴᴇʀ ID: {OWNER_ID}")
    print("📩 Wᴀɪᴛɪɴɢ ғᴏʀ ᴍᴇssᴀɢᴇs...")
    print("✨ Fᴇᴀᴛᴜʀᴇs: Aᴅᴠᴀɴᴄᴇᴅ ᴜsᴇʀ ɪᴅᴇɴᴛɪғɪᴄᴀᴛɪᴏɴ, Tᴡᴏ-ᴡᴀʏ ᴄʜᴀᴛ")
    while True:
        try:
            bot.polling(none_stop=True, timeout=30)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            time.sleep(15)