import telebot
import os
import requests
import json
import threading
import time
import base64
import random
import string
import openai

# 🔹 Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # ✅ OpenAI API Key

# 🔹 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"
GITHUB_SHORTLINKS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/short_links.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN, OPENAI_API_KEY]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, GITHUB_TOKEN, and OPENAI_API_KEY!")

bot = telebot.TeleBot(TOKEN)
openai.api_key = OPENAI_API_KEY  # ✅ Set OpenAI API Key

# 🔹 Load Messages from GitHub
def get_messages():
    try:
        response = requests.get(GITHUB_MESSAGES_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {
            "start": "👋 Welcome! Click below to download your app or chat with AI:",
            "subscribe": "❌ You must subscribe to get the APK. Join here: https://t.me/skmods_000",
            "update": "🔔 New APK Update Available: {app_name}\n📥 Download: {apk_link}"
        }

# 🔹 Load APK Links from GitHub
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

# 🔹 OpenAI GPT-4 AI Chatbot
def get_openai_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["choices"][0]["message"]["content"]
    except Exception:
        return "⚠️ AI service is currently unavailable. Please try again later."

# 🔹 Start Command with AI Chat & APK Download Buttons
@bot.message_handler(commands=["start"])
def handle_start(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", callback_data="download_apk"))
    markup.add(telebot.types.InlineKeyboardButton("🤖 Chat with AI", callback_data="chat_ai"))
    bot.send_message(message.chat.id, "👋 Welcome! Choose an option:", reply_markup=markup)

# 🔹 Handle Callback Queries (AI Chat & APK Download)
@bot.callback_query_handler(func=lambda call: call.data in ["chat_ai", "download_apk"])
def handle_callback(call):
    if call.data == "chat_ai":
        bot.send_message(call.message.chat.id, "🤖 Send me a message, and I will reply as an AI.")
    elif call.data == "download_apk":
        bot.send_message(call.message.chat.id, "🔎 Send the APK name to get the download link.")

# 🔹 Handle AI Chat Messages
@bot.message_handler(func=lambda message: message.reply_to_message and "AI" in message.reply_to_message.text)
def handle_ai_message(message):
    user_text = message.text.strip()
    response = get_openai_response(user_text)
    bot.send_message(message.chat.id, f"🤖 **AI:** {response}")

# 🔹 Handle APK Requests
@bot.message_handler(func=lambda message: True)
def handle_apk_request(message):
    user_id = message.chat.id
    apk_links = get_apk_links()
    app_name = message.text.strip().lower()

    if app_name in apk_links:
        apk_link = apk_links[app_name]

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📥 Download APK", url=apk_link))

        if is_subscribed(user_id):
            bot.send_message(user_id, f"📥 **Download {app_name}:**", reply_markup=markup)
        else:
            messages = get_messages()
            bot.send_message(user_id, messages["subscribe"])
    else:
        bot.send_message(user_id, "⚠️ APK not found. Please check the name or try again later.")

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
