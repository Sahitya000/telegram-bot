import telebot
import os
import requests
import time
import threading

# Bot Token (Railway ENV me set karna)
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# GitHub Raw Links (bot.py me direct store)
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"

if not TOKEN or not CHANNEL_ID:
    raise ValueError("❌ ERROR: Please set BOT_TOKEN and CHANNEL_ID in Railway!")

bot = telebot.TeleBot(TOKEN)

# Function to fetch messages from GitHub
def get_messages():
    default_messages = {
        "start": "Hello! Select an app to download: \n/getapk app_name",
        "subscribe": "❌ You must subscribe to get the APK.\nJoin here: https://t.me/{channel}",
        "update": "🔔 New APK Update Available for {app_name}! 📥\nDownload: {apk_link}"
    }
    try:
        response = requests.get(GITHUB_MESSAGES_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"⚠️ Error fetching messages: {e}")
        return default_messages

# Function to fetch APK links from GitHub
def get_apk_links():
    try:
        response = requests.get(GITHUB_APKS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"⚠️ Error fetching APK links: {e}")
        return {}

# Function to check if user is subscribed
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except telebot.apihelper.ApiTelegramException as e:
        print(f"⚠️ Subscription check failed: {e}")
        return False

# /start command
@bot.message_handler(commands=["start"])
def send_welcome(message):
    messages = get_messages()
    bot.reply_to(message, messages["start"])

# /getapk command for multiple apps
@bot.message_handler(commands=["getapk"])
def send_apk_link(message):
    user_id = message.chat.id
    messages = get_messages()
    apk_links = get_apk_links()

    # Check if user sent app name
    command_parts = message.text.split(" ")
    if len(command_parts) < 2:
        bot.send_message(user_id, "❌ Please use: /getapk app_name\nExample: /getapk instamax")
        return
    
    app_name = command_parts[1].lower().strip()  # Convert app name to lowercase

    # Check if app exists
    if app_name not in apk_links:
        bot.send_message(user_id, f"❌ No APK found for '{app_name}'. Try another app.")
        return

    if is_subscribed(user_id):
        apk_link = apk_links[app_name]
        bot.send_message(user_id, f"📥 Download {app_name}:\n{apk_link}")
    else:
        bot.send_message(user_id, messages["subscribe"].format(channel=CHANNEL_ID))

# Auto-update notifier for multiple apps
def check_for_updates():
    last_apks = {}
    while True:
        try:
            apk_links = get_apk_links()
            messages = get_messages()

            for app_name, apk_link in apk_links.items():
                if app_name not in last_apks or last_apks[app_name] != apk_link:
                    bot.send_message(CHANNEL_ID, messages["update"].format(app_name=app_name, apk_link=apk_link))
                    last_apks[app_name] = apk_link

            time.sleep(3600)  # Check every 1 hour
        except Exception as e:
            print(f"⚠️ Error in update check: {e}")
            time.sleep(60)  # Error aane par 1 minute ke liye wait karega

# Start bot polling in main thread
update_thread = threading.Thread(target=check_for_updates, daemon=True)
update_thread.start()

print("🚀 Bot is running...")
bot.polling()
