import telebot
import os
import requests
import time

# Bot Token & Config (Railway ke ENV me set karna)
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Channel ID or username
GITHUB_MESSAGES_URL = os.getenv("GITHUB_MESSAGES_URL")  # Messages file ka URL
GITHUB_APKS_URL = os.getenv("GITHUB_APKS_URL")  # APK links ka JSON file URL

bot = telebot.TeleBot(TOKEN)

# Function to fetch messages from GitHub
def get_messages():
    default_messages = {
        "start": "Hello! Select an app to download: \n/getapk app_name",
        "subscribe": "❌ You must subscribe to get the APK.\nJoin here: https://t.me/{channel}",
        "update": "🔔 New APK Update Available for {app_name}! 📥\nDownload: {apk_link}"
    }
    try:
        response = requests.get(GITHUB_MESSAGES_URL)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return default_messages

# Function to fetch APK links from GitHub
def get_apk_links():
    try:
        response = requests.get(GITHUB_APKS_URL)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

# Function to check if user is subscribed
def is_subscribed(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
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
    
    app_name = command_parts[1].lower()  # Convert app name to lowercase

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
        apk_links = get_apk_links()
        messages = get_messages()

        for app_name, apk_link in apk_links.items():
            if app_name not in last_apks or last_apks[app_name] != apk_link:
                bot.send_message(CHANNEL_ID, messages["update"].format(app_name=app_name, apk_link=apk_link))
                last_apks[app_name] = apk_link

        time.sleep(3600)  # Check every 1 hour

# Start bot polling
import threading
update_thread = threading.Thread(target=check_for_updates, daemon=True)
update_thread.start()
bot.polling()
