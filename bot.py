import telebot
import os
import requests
import json
import threading
import time
import base64
import random
import string

# 🔹 Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# 🔹 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"
GITHUB_SHORTLINKS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/short_links.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, and GITHUB_TOKEN in Railway!")

bot = telebot.TeleBot(TOKEN)

# 🔹 Load Messages from GitHub
def get_messages():
    try:
        response = requests.get(GITHUB_MESSAGES_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {
            "start": "👋 Welcome! Click below to download your app:",
            "subscribe": "❌ You must subscribe to get the APK. Join here: https://t.me/skmods_000",
            "update": "🔔 New APK Update Available: {app_name}\n📥 Download: {apk_link}"
        }

# 🔹 Load APK Links from GitHub
def get_apk_links():
    try:
        response = requests.get(GITHUB_APKS_URL, timeout=5)
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

# 🔹 Handle /start Command
@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.chat.id
    if is_subscribed(user_id):
        messages = get_messages()
        bot.send_message(user_id, messages["start"])
    else:
        bot.send_message(user_id, messages["subscribe"])

# 🔹 Generate Random Short Code
def generate_short_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

# 🔹 Load Short Links from GitHub
def get_short_links():
    try:
        response = requests.get(GITHUB_SHORTLINKS_API, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=5)
        if response.status_code == 200:
            content = response.json()
            return json.loads(base64.b64decode(content["content"]).decode())
    except requests.RequestException:
        pass
    return {}

# 🔹 Update Short Links on GitHub
def update_short_links(new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(GITHUB_SHORTLINKS_API, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]

        update_data = {
            "message": "Updated Short Links",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }

        update_response = requests.put(GITHUB_SHORTLINKS_API, headers=headers, json=update_data)
        return update_response.status_code == 200
    return False

# 🔹 Handle Direct APK Links (Only Admins Can Send)
@bot.message_handler(func=lambda message: message.text.startswith("http"))
def handle_direct_link(message):
    user_id = message.chat.id
    if is_subscribed(user_id):  # ✅ Check Admin Privileges
        original_link = message.text.strip()
        short_code = generate_short_code()
        short_links = get_short_links()
        short_links[short_code] = original_link
        update_short_links(short_links)  # 🔄 Save to GitHub
        short_link = f"https://t.me/{bot.get_me().username}?start=link_{short_code}"
        bot.send_message(message.chat.id, f"✅ Short link created: {short_link}")
    else:
        bot.send_message(message.chat.id, "❌ You must subscribe to generate links.")

# 🔹 Handle Short Links
@bot.message_handler(commands=["start"])
def handle_short_link(message):
    text = message.text.strip()
    if text.startswith("/start link_"):
        short_code = text.replace("/start link_", "").strip()
        short_links = get_short_links()

        if short_code in short_links:
            user_id = message.chat.id
            original_link = short_links[short_code]

            if is_subscribed(user_id):
                bot.send_message(user_id, f"✅ **Here is your download link:**\n{original_link}")
            else:
                bot.send_message(user_id, "❌ You must subscribe to get the APK.\nJoin here: https://t.me/skmods_000")
        else:
            bot.send_message(message.chat.id, "❌ Invalid or expired link.")

# 🔹 Auto-Delete Chats of Users Who Leave the Channel
def delete_chats_for_left_users():
    while True:
        try:
            updates = bot.get_updates()
            user_ids = set(update.message.chat.id for update in updates if update.message)

            for user_id in user_ids:
                if not is_subscribed(user_id):  # Agar user channel me nahi hai
                    try:
                        bot.send_message(user_id, "⚠️ You left the channel, deleting chat history.")
                        time.sleep(2)  # Thoda delay taaki message visible rahe

                        messages = bot.get_chat_history(user_id, limit=50)
                        for msg in messages:
                            bot.delete_message(user_id, msg.message_id)

                        print(f"🗑 Deleted chat history for user: {user_id}")

                    except Exception as e:
                        print(f"⚠️ Error deleting messages for {user_id}: {e}")

        except Exception as e:
            print(f"⚠️ Background Task Error: {e}")

        time.sleep(3600)  # Har 1 ghante (3600 sec) me check karega

# 🔹 Start Background Task
delete_thread = threading.Thread(target=delete_chats_for_left_users, daemon=True)
delete_thread.start()

print("🚀 Bot is running...")
bot.polling()
