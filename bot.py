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

# 🔹 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_SHORTLINKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/shortlinks.json"
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"
GITHUB_SHORTLINKS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/shortlinks.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, and GITHUB_TOKEN in Railway!")

bot = telebot.TeleBot(TOKEN)


# 🔹 Fetch Data from GitHub
def get_data_from_github(url):
    try:
        response = requests.get(url, timeout=5)
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

# 🔹 Check if User is Admin
def is_admin(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["administrator", "creator"]
    except telebot.apihelper.ApiTelegramException:
        return False

# 🔹 Update GitHub JSON Files
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


# 🔹 /start Command
@bot.message_handler(commands=["start"])
def send_welcome(message):
    messages = get_data_from_github(GITHUB_MESSAGES_URL)
    shortlinks = get_data_from_github(GITHUB_SHORTLINKS_URL)

    text = message.text.split()
    if len(text) > 1 and text[1].startswith("apk_"):
        apk_id = text[1].replace("apk_", "")
        if apk_id in shortlinks:
            apk_link = shortlinks[apk_id]

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=apk_link))

            if is_subscribed(message.chat.id):
                bot.send_message(message.chat.id, f"📥 **Download {apk_id}:**", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, messages.get("subscribe", "❌ Join channel first!"))
        else:
            bot.send_message(message.chat.id, "⚠️ Invalid link!")
    else:
        bot.send_message(message.chat.id, messages.get("start", "👋 Welcome!"))


# 🔹 Shortlink Generation (Admin Only)
@bot.message_handler(commands=["shortlink"])
def create_shortlink(message):
    user_id = message.chat.id
    if not is_admin(user_id):
        bot.send_message(user_id, "⚠️ This feature is only for admins!")
        return

    args = message.text.split(" ", 1)
    if len(args) < 2:
        bot.send_message(user_id, "❌ Usage: /shortlink <apk-name>")
        return

    apk_name = args[1].lower().strip()
    apk_links = get_data_from_github(GITHUB_APKS_URL)

    if apk_name not in apk_links:
        bot.send_message(user_id, "❌ No APK found with that name!")
        return

    short_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    short_link = f"https://t.me/{bot.get_me().username}?start=apk_{short_id}"

    shortlinks = get_data_from_github(GITHUB_SHORTLINKS_URL)
    shortlinks[short_id] = apk_links[apk_name]

    if update_github_file(GITHUB_SHORTLINKS_API, shortlinks):
        bot.send_message(user_id, f"✅ Shortlink Created: {short_link}")
    else:
        bot.send_message(user_id, "⚠️ Error saving short link. Try again later.")


# 🔹 Direct APK Name Input
@bot.message_handler(func=lambda message: True)
def handle_apk_request(message):
    user_id = message.chat.id
    apk_links = get_data_from_github(GITHUB_APKS_URL)

    app_name = message.text.lower().strip()
    if app_name in apk_links:
        apk_link = apk_links[app_name]

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=apk_link))

        if is_subscribed(user_id):
            bot.send_message(user_id, f"📥 **Download {app_name}:**", reply_markup=markup)
        else:
            messages = get_data_from_github(GITHUB_MESSAGES_URL)
            bot.send_message(user_id, messages.get("subscribe", "❌ Join channel first!"))
    else:
        bot.send_message(user_id, "❌ No APK found! Try a different name.")


# 🔹 Handle APK Uploads
@bot.message_handler(content_types=["document"])
def handle_apk_upload(message):
    if message.chat.id != int(CHANNEL_ID):
        return

    file_id = message.document.file_id
    file_name = message.document.file_name.replace(" ", "_").lower()
    
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    
    apk_links = get_data_from_github(GITHUB_APKS_URL)
    apk_links[file_name] = file_url

    if update_github_file(GITHUB_REPO_API, apk_links):
        bot.send_message(CHANNEL_ID, f"✅ {file_name} added to APK database!")
    else:
        bot.send_message(CHANNEL_ID, "⚠️ Error updating APK list on GitHub.")


# 🔹 Background Thread: Auto-check for updates
def check_for_updates():
    last_apks = get_data_from_github(GITHUB_APKS_URL)
    while True:
        apk_links = get_data_from_github(GITHUB_APKS_URL)
        messages = get_data_from_github(GITHUB_MESSAGES_URL)

        for app_name, apk_link in apk_links.items():
            if last_apks.get(app_name) != apk_link:
                bot.send_message(CHANNEL_ID, messages.get("update", "New update available!").format(app_name=app_name, apk_link=apk_link))
                last_apks[app_name] = apk_link

        time.sleep(3600)

update_thread = threading.Thread(target=check_for_updates, daemon=True)
update_thread.start()

print("🚀 Bot is running...")
bot.polling()
