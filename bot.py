import telebot
import os
import requests
import json
import threading
import time
import base64

# 🔹 Load Environment Variables from Railway
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# 🔹 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_SHORTLINKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/short_links.json"
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"
GITHUB_SHORTLINKS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/short_links.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, and GITHUB_TOKEN in Railway!")

bot = telebot.TeleBot(TOKEN)

# 🔹 Fetch Short Links from GitHub
def get_short_links():
    try:
        response = requests.get(GITHUB_SHORTLINKS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Check Subscription
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except telebot.apihelper.ApiTelegramException:
        return False

# 🔹 Generate Short URL (Only for Admin)
@bot.message_handler(commands=["short"])
def generate_short_link(message):
    user_id = message.chat.id
    if user_id != int(CHANNEL_ID):
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

# 🔹 Handle Short Links (With Subscription Check)
@bot.message_handler(commands=["start"])
def handle_start(message):
    command_parts = message.text.split(" ", 1)
    if len(command_parts) == 2:
        short_code = command_parts[1]
        short_links = get_short_links()

        if short_code in short_links:
            user_id = message.chat.id
            if is_subscribed(user_id):
                bot.send_message(user_id, f"📥 **Download Your APK:** {short_links[short_code]}")
            else:
                messages = get_messages()
                bot.send_message(user_id, messages["subscribe"].format(channel=CHANNEL_ID))
            return
    
    messages = get_messages()
    bot.send_message(message.chat.id, messages["start"])

print("🚀 Bot is running...")
bot.polling()
