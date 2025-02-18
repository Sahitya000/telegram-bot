import telebot
import os
import requests
import json
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
GITHUB_BLACKLIST_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/blacklist.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, and GITHUB_TOKEN in Railway!")

bot = telebot.TeleBot(TOKEN)

# 🔹 Get Blacklist from GitHub
def get_blacklist():
    try:
        response = requests.get(GITHUB_BLACKLIST_API, timeout=5)
        response.raise_for_status()
        content_data = response.json()
        file_content = base64.b64decode(content_data["content"]).decode()
        return json.loads(file_content)
    except requests.RequestException:
        return []

# 🔹 Check if User is Blacklisted
def is_blacklisted(user_id):
    blacklist = get_blacklist()
    return str(user_id) in blacklist

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

# 🔹 Get APK Links from GitHub
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

# 🔹 Handle APK Requests
@bot.message_handler(func=lambda message: True)
def handle_apk_request(message):
    user_id = message.chat.id

    if is_blacklisted(user_id):
        bot.send_message(user_id, "❌ You are blacklisted and cannot access APKs.")
        return

    apk_links = get_apk_links()
    app_name = message.text.strip().lower()
    
    matching_apk = next((key for key in apk_links if app_name in key.lower()), None)

    if matching_apk:
        apk_link = apk_links[matching_apk]

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=apk_link))

        if is_subscribed(user_id):
            bot.send_message(user_id, f"📥 **Download {matching_apk}:**", reply_markup=markup)
        else:
            messages = get_messages()
            bot.send_message(user_id, messages["subscribe"])
    else:
        bot.send_message(user_id, "⚠️ Error ⚠️\nMay be you entered wrong name of APK. Try again later 😞\nSend this message to @sks_000")

# 🔹 Handle Short Links
@bot.message_handler(func=lambda message: message.text.startswith("/start link_"))
def handle_short_link(message):
    user_id = message.chat.id

    if is_blacklisted(user_id):
        bot.send_message(user_id, "❌ You are blacklisted and cannot access APKs.")
        return

    short_code = message.text.split("_")[-1]
    apk_links = get_apk_links()

    if short_code in apk_links:
        apk_data = apk_links[short_code]
        if is_subscribed(user_id):
            bot.send_message(user_id, f"✅ Here is your APK link:\n🔹 Name: {apk_data['name']}\n🔹 Link: {apk_data['link']}")
        else:
            bot.send_message(user_id, "❌ You must join the channel first to get the APK link.")
    else:
        bot.send_message(user_id, "⚠️ Invalid or expired short link.")

# 🔹 Handle APK List
@bot.message_handler(commands=["applist"])
def handle_applist(message):
    user_id = message.chat.id

    if is_blacklisted(user_id):
        bot.send_message(user_id, "❌ You are blacklisted and cannot access APKs.")
        return

    apk_links = get_apk_links()

    if not apk_links:
        bot.send_message(user_id, "⚠️ No APKs found in the repository.")
        return

    if not is_subscribed(user_id):
        messages = get_messages()
        bot.send_message(user_id, messages["subscribe"])
        return

    text = "📱 **Available Apps:**\n\n"

    for app_name, apk_link in apk_links.items():
        text += f"🎯 **{app_name}**\n🔗 [Click here to download]({apk_link})\n\n"

    bot.send_message(user_id, text, parse_mode="Markdown", disable_web_page_preview=True)

# 🔹 Ensure Bot Runs Continuously
if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Bot crashed: {e}")
            time.sleep(5)
