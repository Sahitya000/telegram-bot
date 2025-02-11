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

# 🔹 Fetch Messages
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

# 🔹 Fetch APK Links
def get_apk_links():
    try:
        response = requests.get(GITHUB_APKS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Fetch Short Links
def get_short_links():
    try:
        response = requests.get(GITHUB_SHORTLINKS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Update GitHub Data
def update_github_data(url, new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]
        update_data = {
            "message": "Updated data",
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

# 🔹 Generate Short Link (Admin Only)
@bot.message_handler(commands=["short"])
def generate_short_link(message):
    user_id = message.chat.id
    if not is_admin(user_id):
        bot.send_message(user_id, "❌ Sirf channel admins short link bana sakte hain!")
        return

    command_parts = message.text.split(" ", 1)
    if len(command_parts) < 2:
        bot.send_message(user_id, "❌ Use: /short <apk_name>")
        return

    apk_name = command_parts[1].strip().lower()
    apk_links = get_apk_links()

    if apk_name not in apk_links:
        bot.send_message(user_id, f"❌ APK '{apk_name}' database me nahi hai!")
        return

    short_code = f"sk_{int(time.time())}"
    short_link = f"https://t.me/{bot.get_me().username}?start={short_code}"

    short_links = get_short_links()
    short_links[short_code] = apk_name

    if update_github_data(GITHUB_SHORTLINKS_API, short_links):
        bot.send_message(user_id, f"✅ Short Link Created for {apk_name}: {short_link}")
    else:
        bot.send_message(user_id, "⚠️ Error updating short links on GitHub.")

# 🔹 Handle Short Links (Check Subscription)
@bot.message_handler(commands=["start"])
def handle_start(message):
    command_parts = message.text.split(" ", 1)
    if len(command_parts) == 2:
        short_code = command_parts[1]
        short_links = get_short_links()

        if short_code in short_links:
            apk_name = short_links[short_code]
            apk_links = get_apk_links()

            if apk_name in apk_links:
                user_id = message.chat.id

                if is_subscribed(user_id):
                    bot.send_message(user_id, f"📥 Your Download Link:\n{apk_links[apk_name]}")
                else:
                    messages = get_messages()
                    bot.send_message(user_id, messages["subscribe"].format(channel=CHANNEL_ID))
                return
    
    messages = get_messages()
    bot.send_message(message.chat.id, messages["start"])

# 🔹 Direct APK Name Input
@bot.message_handler(func=lambda message: True)
def handle_apk_request(message):
    user_id = message.chat.id
    apk_links = get_apk_links()

    app_name = message.text.lower().strip()
    if app_name in apk_links:
        apk_link = apk_links[app_name]

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=apk_link))

        if is_subscribed(user_id):
            bot.send_message(user_id, f"📥 **Download {app_name}:**", reply_markup=markup)
        else:
            messages = get_messages()
            bot.send_message(user_id, messages["subscribe"].format(channel=CHANNEL_ID))
    else:
        bot.send_message(user_id, "❌ Koi APK nahi mila! Sahi naam likho ya /getapk use karo.")

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

    if update_github_data(GITHUB_REPO_API, apk_links):
        bot.send_message(CHANNEL_ID, f"✅ {file_name} added to APK database!")
    else:
        bot.send_message(CHANNEL_ID, "⚠️ Error updating APK list on GitHub.")

# 🔹 Check Subscription
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except telebot.apihelper.ApiTelegramException:
        return False

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
