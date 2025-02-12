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
GITHUB_SHORTLINKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/shortlink.json"

GITHUB_REPO_APKS = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"
GITHUB_REPO_SHORTLINKS = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/shortlink.json"

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
            "subscribe": "❌ You must subscribe to get the APK. Join here: https://t.me/{channel}"
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
        response = requests.get(GITHUB_SHORTLINKS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Update GitHub Data
def update_github_data(repo_url, new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(repo_url, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]
        
        update_data = {
            "message": "Updated data",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }
        
        update_response = requests.put(repo_url, headers=headers, json=update_data)
        return update_response.status_code == 200
    return False

# 🔹 Check Subscription
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except telebot.apihelper.ApiTelegramException:
        return False

# 🔹 Generate Unique Short Code
def generate_short_code():
    return str(int(time.time()))

# 🔹 /start Command
@bot.message_handler(commands=["start"])
def send_welcome(message):
    messages = get_messages()
    
    if message.text.startswith("/start short_"):
        short_code = message.text.split("_", 1)[1]
        short_links = get_short_links()

        if short_code in short_links:
            if is_subscribed(message.chat.id):
                bot.send_message(message.chat.id, f"🔗 **Redirecting to your link:** {short_links[short_code]}")
            else:
                subscribe_message = messages["subscribe"].format(channel=CHANNEL_ID)
                bot.send_message(message.chat.id, subscribe_message)
        else:
            bot.send_message(message.chat.id, "❌ Invalid short link!")
    else:
        bot.send_message(message.chat.id, messages["start"])

# 🔹 /shortlink Command (Admin Only)
@bot.message_handler(commands=["shortlink"])
def create_shortlink(message):
    user_id = message.chat.id

    # 🔹 Check if user is admin
    chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
    if chat_member.status not in ["administrator", "creator"]:
        bot.send_message(user_id, "❌ Only admins can create short links!")
        return

    # 🔹 Process command
    command_parts = message.text.split(" ", 1)
    if len(command_parts) < 2 or not command_parts[1].startswith("http"):
        bot.send_message(user_id, "❌ Usage: `/shortlink http://yourlink.com`")
        return
    
    original_link = command_parts[1].strip()
    short_code = generate_short_code()

    short_links = get_short_links()
    short_links[short_code] = original_link

    if update_github_data(GITHUB_REPO_SHORTLINKS, short_links):
        bot.send_message(user_id, f"✅ Short link created: https://t.me/{bot.get_me().username}?start=short_{short_code}")
    else:
        bot.send_message(user_id, "⚠️ Error updating short links on GitHub.")

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

    if update_github_data(GITHUB_REPO_APKS, apk_links):
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
