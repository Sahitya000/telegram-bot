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
OWNER_ID = os.getenv("OWNER_ID")  # 🔥 Tumhara Telegram ID yahan set karo
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# 🔹 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN, OWNER_ID]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, GITHUB_TOKEN, and OWNER_ID in Railway!")

bot = telebot.TeleBot(TOKEN)

# 🔹 Short Links Storage (GitHub)
SHORT_LINKS_FILE = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/short_links.json"
GITHUB_SHORTLINK_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/short_links.json"

# 🔹 GitHub se Data Fetch Karna
def get_data_from_github(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 GitHub me Data Update Karna
def update_github_data(api_url, new_data):
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

# 🔹 Random Short Link Generator
def generate_random_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# 🔹 Short Link Generate & Owner Ko Send Karna
def send_short_link_to_owner(app_name, apk_link):
    short_code = generate_random_code()
    short_links = get_data_from_github(SHORT_LINKS_FILE)
    short_links[short_code] = {"app_name": app_name, "apk_link": apk_link}

    if update_github_data(GITHUB_SHORTLINK_API, short_links):
        short_url = f"https://t.me/{bot.get_me().username}?start=apk_{short_code}"
        message = f"📢 **New APK Short Link Generated**\n\n🔹 **App Name:** {app_name}\n🔗 **Short Link:** {short_url}\n\n✅ Share this link manually."
        bot.send_message(OWNER_ID, message)
    else:
        bot.send_message(OWNER_ID, "⚠️ Error generating short link!")

# 🔹 /start Command - Handle Short Links
@bot.message_handler(commands=["start"])
def send_welcome(message):
    text = message.text.strip().split()
    if len(text) == 2 and text[1].startswith("apk_"):
        short_code = text[1][4:]
        short_links = get_data_from_github(SHORT_LINKS_FILE)

        if short_code in short_links:
            app_info = short_links[short_code]

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=app_info["apk_link"]))

            bot.send_message(message.chat.id, f"📌 **APK Board**\n\n📱 **App:** {app_info['app_name']}\n🔗 **Download Link:**", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "❌ Invalid Link!")
    else:
        messages = get_data_from_github(GITHUB_MESSAGES_URL)
        bot.send_message(message.chat.id, messages["start"])

# 🔹 Direct APK Name Input - Generate Short Link
@bot.message_handler(func=lambda message: True)
def handle_apk_request(message):
    user_id = message.chat.id
    apk_links = get_data_from_github(GITHUB_APKS_URL)

    app_name = message.text.lower().strip()
    if app_name in apk_links:
        send_short_link_to_owner(app_name, apk_links[app_name])
        bot.send_message(user_id, "🔹 **Request received! Owner will share the link soon.**")
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

    apk_links = get_data_from_github(GITHUB_APKS_URL)
    apk_links[file_name] = file_url

    if update_github_data(GITHUB_REPO_API, apk_links):
        bot.send_message(CHANNEL_ID, f"✅ {file_name} added to APK database!")
        send_short_link_to_owner(file_name, file_url)  # 🔥 Jab bhi APK upload hoga, owner ko short link milega
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
                bot.send_message(CHANNEL_ID, messages["update"].format(app_name=app_name, apk_link=apk_link))
                last_apks[app_name] = apk_link

        time.sleep(3600)

update_thread = threading.Thread(target=check_for_updates, daemon=True)
update_thread.start()

print("🚀 Bot is running...")
bot.polling()
