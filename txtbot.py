import telebot
from telebot import types
import os
from flask import Flask
from werkzeug.serving import run_simple

BOT_TOKEN = "7120774765:AAG-Ut25oOwSxlF-kUQ5k2nTjGZiw42UVuo"
CHANNEL_USERNAME = "botsproupdates"  # Without @
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

# Force join check
def check_user_joined(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Start command
@bot.message_handler(commands=['start'])
def start(message):
    if not check_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join our Channel 🔔", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(message.chat.id,
            "<b>Welcome to the Text-to-File Bot! 🎉</b>\n\n"
            "<b>You need to join our channel to use this bot. 📝</b>",
            parse_mode="HTML", reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Owner 🙂", url="https://t.me/zeus_is_here"))
    bot.send_message(message.chat.id,
        "<b>Welcome to the Text-to-File Bot! 🎉</b>\n\n"
        "<b>This bot allows you to convert text into various file formats. Use /textfile to get started. 📂</b>",
        parse_mode="HTML", reply_markup=markup)

# /textfile command
@bot.message_handler(commands=['textfile'])
def textfile(message):
    if not check_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join our Channel 🔔", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(message.chat.id,
            "<b>You need to join our channel to use this feature. 📝</b>",
            parse_mode="HTML", reply_markup=markup)
        return

    # Arranging buttons in 3 rows
    markup = types.InlineKeyboardMarkup(row_width=3)  # Three buttons per row
    rows = [
        [types.InlineKeyboardButton(f"{emoji} {ext.upper()}", callback_data=f"format_{ext}") for ext, emoji in FORMATS[i:i+3]] 
        for i in range(0, len(FORMATS), 3)
    ]
    markup.add(*[button for row in rows for button in row])  # Flatten rows and add buttons to markup

    bot.send_message(message.chat.id, "<b>Choose a file format to save your text: 📑</b>", parse_mode="HTML", reply_markup=markup)

# Format selection handler
@bot.callback_query_handler(func=lambda call: call.data.startswith("format_"))
def handle_format(call):
    ext = call.data.split("_")[1]
    user_format[call.from_user.id] = ext
    msg = bot.send_message(call.message.chat.id, f"<b>Great! Send me the text to save as .{ext} ✍️</b>", parse_mode="HTML")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# Text input after format selection
@bot.message_handler(func=lambda m: m.from_user.id in user_format)
def get_text(message):
    ext = user_format.pop(message.from_user.id)
    text = message.text
    file_name = f"text_file.{ext}"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(text)
    with open(file_name, "rb") as doc:
        sent = bot.send_document(message.chat.id, doc, caption=f"<b>Your file is ready: {file_name}</b>\n<b>Want to rename it?</b>\nSend the new name with extension.", parse_mode="HTML")
    os.remove(file_name)
    user_text[message.from_user.id] = text
    bot.delete_message(message.chat.id, message.message_id)

# Rename file
@bot.message_handler(func=lambda m: m.from_user.id in user_text)
def rename_file(message):
    name = message.text.strip()
    if '.' not in name or name.split('.')[-1] == '':
        bot.reply_to(message, "<b>Invalid format! Include a valid extension like .txt, .py</b>", parse_mode="HTML")
        return
    text = user_text.pop(message.from_user.id)
    with open(name, "w", encoding="utf-8") as f:
        f.write(text)
    with open(name, "rb") as doc:
        bot.send_document(message.chat.id, doc, caption=f"<b>Renamed and sent: {name}</b>", parse_mode="HTML")
    os.remove(name)
    bot.delete_message(message.chat.id, message.message_id)

# Split file command
@bot.message_handler(commands=['spl'])
def split_file(message):
    try:
        parts = message.text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            raise ValueError
        lines = int(parts[1])
        if lines < 50 or lines > 500:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "<b>Usage: /spl 300</b>\n<b>Line count must be between 50 and 500.</b>", parse_mode="HTML")
        return

    msg = message.reply_to_message
    if not msg or not msg.document:
        bot.reply_to(message, "<b>Reply to a text file with this command to split it.</b>", parse_mode="HTML")
        return

    file_info = bot.get_file(msg.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    content = downloaded.decode("utf-8")
    lines_list = content.splitlines()
    chunks = [lines_list[i:i + lines] for i in range(0, len(lines_list), lines)]

    for i, chunk in enumerate(chunks, start=1):
        filename = f"part_{i}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write('\n'.join(chunk))
        with open(filename, "rb") as doc:
            bot.send_document(message.chat.id, doc, caption=f"<b>Split part {i}</b>", parse_mode="HTML")
        os.remove(filename)
    bot.delete_message(message.chat.id, message.message_id)

# Flask app to keep the bot alive
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

if __name__ == '__main__':
    # Run Flask app on Render
    bot.remove_webhook()
    bot.set_webhook(url='https://your-render-app-url.com')  # Replace with your render app URL
    run_simple('0.0.0.0', 5000, app)