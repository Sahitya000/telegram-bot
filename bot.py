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
def fetch_from_github(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Update Data on GitHub
def update_github_data(api_url, new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]

        update_data = {
            "message": "Updated data",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }

        update_response = requests.put(api_url, headers=headers, json=update_data)
        return update_response.status_code == 200
    return False

# 🔹 Generate Random Short Link Key
def generate_short_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

# 🔹 /shortlink Command
@bot.message_handler(commands=["shortlink"])
def create_short_link(message):
    user_id = message.chat.id
    args = message.text.split(" ", 1)

    if len(args) < 2:
        bot.send_message(user_id, "❌ Usage: /shortlink <APK download link>")
        return

    original_link = args[1].strip()
    
    shortlinks = fetch_from_github(GITHUB_SHORTLINKS_URL)
    
    # Pehle check kare ki link pehle se shortlinks me hai
    for key, value in shortlinks.items():
        if value == original_link:
            short_url = f"https://t.me/{bot.get_me().username}?start=short_{key}"
            bot.send_message(user_id, f"✅ Short Link: {short_url}")
            return

    # Naya short key generate karna
    short_key = generate_short_key()
    shortlinks[short_key] = original_link

    if update_github_data(GITHUB_SHORTLINKS_API, shortlinks):
        short_url = f"https://t.me/{bot.get_me().username}?start=short_{short_key}"
        bot.send_message(user_id, f"✅ Short Link Created: {short_url}")
    else:
        bot.send_message(user_id, "⚠️ Error saving short link. Try again later.")

# 🔹 /start Handler for Short Links
@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.chat.id
    args = message.text.split("_", 1)

    # Agar koi short link ka request hai
    if len(args) == 2 and args[0] == "/start":
        short_key = args[1]
        shortlinks = fetch_from_github(GITHUB_SHORTLINKS_URL)

        if short_key in shortlinks:
            original_link = shortlinks[short_key]
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=original_link))
            bot.send_message(user_id, f"🔗 Here is your original link:", reply_markup=markup)
            return

    # Default welcome message
    messages = fetch_from_github(GITHUB_MESSAGES_URL)
    bot.send_message(user_id, messages.get("start", "👋 Welcome! Click below to download your app:"))

# 🔹 Direct APK Name Input
@bot.message_handler(func=lambda message: True)
def handle_apk_request(message):
    user_id = message.chat.id
    apk_links = fetch_from_github(GITHUB_APKS_URL)

    app_name = message.text.lower().strip()
    if app_name in apk_links:
        apk_link = apk_links[app_name]

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=apk_link))

        if is_subscribed(user_id):
            bot.send_message(user_id, f"📥 **Download {app_name}:**", reply_markup=markup)
        else:
            messages = fetch_from_github(GITHUB_MESSAGES_URL)
            bot.send_message(user_id, messages.get("subscribe", "❌ You must subscribe to get the APK."))
    else:
        bot.send_message(user_id, "❌ Koi APK nahi mila! Sahi naam likho ya /getapk use karo.")

# 🔹 Background Thread: Auto-check for updates
def check_for_updates():
    last_apks = fetch_from_github(GITHUB_APKS_URL)
    while True:
        apk_links = fetch_from_github(GITHUB_APKS_URL)
        messages = fetch_from_github(GITHUB_MESSAGES_URL)

        for app_name, apk_link in apk_links.items():
            if last_apks.get(app_name) != apk_link:
                bot.send_message(CHANNEL_ID, messages.get("update", "🔔 New APK Update Available: {app_name}\n📥 Download: {apk_link}").format(app_name=app_name, apk_link=apk_link))
                last_apks[app_name] = apk_link

        time.sleep(3600)

update_thread = threading.Thread(target=check_for_updates, daemon=True)
update_thread.start()

print("🚀 Bot is running...")
bot.polling()
