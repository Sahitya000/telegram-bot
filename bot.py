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
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"

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

# 🔹 Check Subscription
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except telebot.apihelper.ApiTelegramException:
        return False

# 🔹 Generate Short URL (Fixed)
def generate_short_url(apk_name):
    return f"https://t.me/{bot.get_me().username}?start=apk_{apk_name}"

# 🔹 Update APK Links on GitHub (Fixed Encoding Issue)
def update_github_apk_links(new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(GITHUB_REPO_API, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]
        
        update_data = {
            "message": "Updated APK links",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }
        
        update_response = requests.put(GITHUB_REPO_API, headers=headers, json=update_data)
        return update_response.status_code == 200
    return False

# 🔹 /start Command
@bot.message_handler(commands=["start"])
def send_welcome(message):
    messages = get_messages()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔎 Get APK", callback_data="getapk"))
    bot.send_message(message.chat.id, messages["start"], reply_markup=markup)

# 🔹 /getapk Command
@bot.message_handler(commands=["getapk"])
def send_apk_link(message):
    user_id = message.chat.id
    apk_links = get_apk_links()

    command_parts = message.text.split(" ")
    if len(command_parts) < 2:
        bot.send_message(user_id, "❌ Please use: /getapk app_name\nExample: /getapk instamax")
        return

    app_name = command_parts[1].lower().strip()
    if app_name not in apk_links:
        bot.send_message(user_id, f"❌ No APK found for '{app_name}'. Try another app.")
        return

    apk_link = generate_short_url(app_name)

    if is_subscribed(user_id):
        bot.send_message(user_id, f"📥 Download {app_name}:\n{apk_link}")
    else:
        messages = get_messages()
        bot.send_message(user_id, messages["subscribe"].format(channel=CHANNEL_ID))

# 🔹 Inline Button Click Handler (Fixed)
@bot.callback_query_handler(func=lambda call: call.data.startswith("getapk_"))
def send_apk_link_callback(call):
    apk_name = call.data.replace("getapk_", "")
    apk_links = get_apk_links()

    if apk_name in apk_links:
        apk_link = generate_short_url(apk_name)
        bot.send_message(call.message.chat.id, f"📥 Download **{apk_name}**: {apk_link}", parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id, "❌ APK link not found!")

# 🔹 Handle APK Uploads (Fixed Auto-Update GitHub)
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

    if update_github_apk_links(apk_links):
        bot.send_message(CHANNEL_ID, f"✅ {file_name} added to APK database!")
    else:
        bot.send_message(CHANNEL_ID, "⚠️ Error updating APK list on GitHub.")

# 🔹 Auto-send APK when user joins channel (Fixed)
@bot.message_handler(func=lambda message: message.new_chat_members is not None)
def welcome_new_member(message):
    user_id = message.chat.id
    apk_links = get_apk_links()

    if apk_links:
        latest_apk = list(apk_links.keys())[-1]
        apk_link = generate_short_url(latest_apk)
        bot.send_message(user_id, f"🎉 Welcome! Get the latest APK:\n{apk_link}")

# 🔹 Background Thread: Auto-check for updates (Fixed)
def check_for_updates():
    last_apks = get_apk_links()
    while True:
        apk_links = get_apk_links()
        messages = get_messages()

        for app_name, apk_link in apk_links.items():
            if last_apks.get(app_name) != apk_link:
                bot.send_message(CHANNEL_ID, messages["update"].format(app_name=app_name, apk_link=generate_short_url(app_name)))
                last_apks[app_name] = apk_link
        
        time.sleep(3600)

update_thread = threading.Thread(target=check_for_updates, daemon=True)
update_thread.start()

print("🚀 Bot is running...")
bot.polling()
