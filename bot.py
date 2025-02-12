import telebot
import os
import requests
import json
import threading
import time
import base64
import random
import string

# 🔹 Load Environment Variables from Railway
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ADMIN_IDS = [5642910026, 987654321]  # Replace with actual admin Telegram IDs

# 🔹 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_SHORTLINK_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/shortlink.json"
GITHUB_SHORTLINK_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/shortlink.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, and GITHUB_TOKEN in Railway!")

bot = telebot.TeleBot(TOKEN)

# 🔹 Fetch Messages from GitHub
def get_messages():
    try:
        response = requests.get(GITHUB_MESSAGES_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {
            "start": "👋 Welcome! Click below to download your app:",
            "subscribe": "❌ You must subscribe to get the APK. Join here: https://t.me/{channel}",
            "update": "🔔 New APK Update Available: {app_name}\n📥 Download: {apk_link}"
        }

# 🔹 Fetch APK Links from GitHub
def get_apk_links():
    try:
        response = requests.get(GITHUB_APKS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Fetch Short Links from GitHub
def get_short_links():
    try:
        response = requests.get(GITHUB_SHORTLINK_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Update GitHub File
def update_github_file(api_url, new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]
        
        update_data = {
            "message": "Updated Data",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }
        
        update_response = requests.put(api_url, headers=headers, json=update_data)
        return update_response.status_code == 200
    return False

# 🔹 Generate Short Code
def generate_short_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

# 🔹 Check Subscription
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except telebot.apihelper.ApiTelegramException:
        return False

# 🔹 /shorten Command (Admin Only)
@bot.message_handler(commands=["shorten"])
def create_short_link(message):
    user_id = message.chat.id
    if user_id not in ADMIN_IDS:
        bot.send_message(user_id, "🚨 **Only admins can create short links!**")
        return

    args = message.text.split(" ", 1)
    if len(args) < 2:
        bot.send_message(user_id, "❌ Usage: /shorten <apk_name>")
        return

    apk_name = args[1].lower().strip()
    apk_links = get_apk_links()
    short_links = get_short_links()

    if apk_name not in apk_links:
        bot.send_message(user_id, "❌ APK not found! Make sure the name is correct.")
        return

    short_code = generate_short_code()
    short_links[short_code] = apk_links[apk_name]

    if update_github_file(GITHUB_SHORTLINK_API, short_links):
        short_url = f"https://t.me/{bot.get_me().username}?start={short_code}"
        bot.send_message(user_id, f"✅ **Short link created:** {short_url}")
    else:
        bot.send_message(user_id, "⚠️ Error updating short link on GitHub.")

# 🔹 /start Command (Short Link Access)
@bot.message_handler(commands=["start"])
def handle_short_link(message):
    user_id = message.chat.id
    args = message.text.split(" ", 1)

    if len(args) == 1:
        bot.send_message(user_id, get_messages()["start"])
        return

    short_code = args[1].strip()
    short_links = get_short_links()

    if short_code not in short_links:
        bot.send_message(user_id, "❌ Invalid short link!")
        return

    if is_subscribed(user_id):
        apk_link = short_links[short_code]
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=apk_link))
        bot.send_message(user_id, f"✅ Here is your link:", reply_markup=markup)
    else:
        bot.send_message(user_id, get_messages()["subscribe"].format(channel=CHANNEL_ID))

# 🔹 Handle APK Uploads
@bot.message_handler(content_types=["document"])
def handle_apk_upload(message):
    if message.chat.id != int(CHANNEL_ID):
        return

    file_id = message.document.file_id
    file_name = message.document.file_name.replace(" ", "_").lower()
    
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    
    apk_links = get_apk_links()
    apk_links[file_name] = file_url

    if update_github_file(GITHUB_APKS_URL, apk_links):
        bot.send_message(CHANNEL_ID, f"✅ {file_name} added to APK database!")
    else:
        bot.send_message(CHANNEL_ID, "⚠️ Error updating APK list on GitHub.")

# 🔹 Background Thread: Auto-check for updates
def check_for_updates():
    last_apks = get_apk_links()
    while True:
        apk_links = get_apk_links()
        messages = get_messages()

        for app_name, apk_link in apk_links.items():
            if last_apks.get(app_name) != apk_link:
                bot.send_message(CHANNEL_ID, messages["update"].format(app_name=app_name, apk_link=apk_link))
                last_apks[app_name] = apk_link

        time.sleep(3600)

update_thread = threading.Thread(target=check_for_updates, daemon=True)
update_thread.start()

print("🚀 Bot is running...")
bot.polling()
