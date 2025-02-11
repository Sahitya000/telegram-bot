import telebot
import os
import requests
import json
import threading
import time
import base64

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# 🔹 GitHub URLs
GITHUB_SHORTLINKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/short_links.json"
GITHUB_SHORTLINKS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/short_links.json"

bot = telebot.TeleBot(TOKEN)

# 🔹 Fetch Short Links
def get_short_links():
    try:
        response = requests.get(GITHUB_SHORTLINKS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Update Short Links on GitHub
def update_github_data(url, new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]

        update_data = {
            "message": "Updated short links",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }

        update_response = requests.put(url, headers=headers, json=update_data)
        return update_response.status_code == 200
    return False

# 🔹 Admin Check
def is_admin(user_id):
    try:
        chat_admins = bot.get_chat_administrators(CHANNEL_ID)
        return any(admin.user.id == user_id for admin in chat_admins)
    except telebot.apihelper.ApiTelegramException:
        return False

# 🔹 Check Subscription
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except telebot.apihelper.ApiTelegramException:
        return False

# 🔹 Generate Short Link
@bot.message_handler(commands=["short"])
def generate_short_link(message):
    user_id = message.chat.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sirf channel admins short link bana sakte hain!")
        return

    command_parts = message.text.split(" ", 1)
    if len(command_parts) < 2:
        bot.send_message(user_id, "❌ Use: /short <actual_apk_link>")
        return

    original_link = command_parts[1].strip()
    short_code = f"sk_{int(time.time())}"
    short_link = f"https://t.me/{bot.get_me().username}?start={short_code}"

    short_links = get_short_links()
    short_links[short_code] = original_link

    if update_github_data(GITHUB_SHORTLINKS_API, short_links):
        bot.send_message(user_id, f"✅ Short Link Created: {short_link}")
    else:
        bot.send_message(user_id, "⚠️ Error updating short links on GitHub.")

# 🔹 Handle Short Links with Subscription Check
@bot.message_handler(commands=["start"])
def handle_start(message):
    command_parts = message.text.split(" ", 1)
    if len(command_parts) == 2:
        short_code = command_parts[1]
        short_links = get_short_links()

        if short_code in short_links:
            if is_subscribed(message.chat.id):
                bot.send_message(message.chat.id, f"📥 Download Link: {short_links[short_code]}")
            else:
                keyboard = telebot.types.InlineKeyboardMarkup()
                keyboard.add(telebot.types.InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{CHANNEL_ID}"))
                bot.send_message(message.chat.id, "⚠ You must join the channel to access this link.", reply_markup=keyboard)
            return
    
    bot.send_message(message.chat.id, "👋 Welcome! Use /getapk to download an app.")

# 🚀 Start Bot
print("🚀 Bot is running...")
bot.polling()
