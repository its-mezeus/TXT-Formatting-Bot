import os
from flask import Flask, request
import telebot
from telebot import types
from urllib.parse import urlparse
import re

# === Configuration ===
BOT_TOKEN = "7120774765:AAEEivSZelVYobwsJLK0g3KWCY2LX7aN48U"
CHANNEL_USERNAME = "botsproupdates"
WEBHOOK_URL = f"https://txt-formatting-bot.onrender.com/{BOT_TOKEN}"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# === Data Storage ===
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

# === Helper Function ===
def check_user_joined(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# === Handlers ===

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
        "<b>Welcome to the Text-to-File Bot! 🎉</b>\n\n<b>Use /textfile to start converting text to file.</b>\n<b>Use /spl [ 50 TO 500 LINES ] (reply to TXT) to split large files.</b>\n<b>Use /clean (reply to TXT) to remove duplicate domains.</b>",
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
        bot.reply_to(message, "<b>Reply to a TXT file to split it.</b>", parse_mode="HTML")
        return

    file_info = bot.get_file(reply.document.file_id)
    content = bot.download_file(file_info.file_path).decode("utf-8")
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
def clean_duplicates(message):
    reply = message.reply_to_message
    if not reply or not reply.document:
        bot.reply_to(message, "<b>Reply to a .txt file to clean it (remove duplicate domains).</b>", parse_mode="HTML")
        return

    file_info = bot.get_file(reply.document.file_id)
    content = bot.download_file(file_info.file_path).decode("utf-8")
    lines = content.splitlines()

    seen_domains = set()
    unique_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.search(r'https?://[^\s]+', line)
        if match:
            domain = urlparse(match.group()).netloc.lower()
            if domain not in seen_domains:
                seen_domains.add(domain)
                unique_lines.append(line)
        else:
            unique_lines.append(line)

    cleaned_name = "cleaned_urls.txt"
    with open(cleaned_name, "w", encoding="utf-8") as f:
        f.write('\n'.join(unique_lines))
    with open(cleaned_name, "rb") as f:
        bot.send_document(message.chat.id, f, caption="<b>Cleaned file (duplicates removed by domain)</b>", parse_mode="HTML")
    os.remove(cleaned_name)

# === Flask Webhook ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "<h3>Bot is Live</h3>"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
