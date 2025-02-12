import telebot
import os
import requests
import json
import threading
import time
import base64
import random
import string
import google.generativeai as genai

# 🔹 Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🔹 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"
GITHUB_SHORTLINKS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/short_links.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN, GEMINI_API_KEY]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, GITHUB_TOKEN, and GEMINI_API_KEY in Railway!")

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# 🔹 Gemini AI Response Function
def get_gemini_response(prompt):
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "⚠️ AI Error: " + str(e)

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

# 🔹 Load Short Links from GitHub
def get_short_links():
    try:
        response = requests.get(GITHUB_SHORTLINKS_API, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=5)
        if response.status_code == 200:
            content = response.json()
            return json.loads(base64.b64decode(content["content"]).decode())
    except requests.RequestException:
        pass
    return {}

# 🔹 Update Short Links on GitHub
def update_short_links(new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(GITHUB_SHORTLINKS_API, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]

        update_data = {
            "message": "Updated Short Links",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }

        update_response = requests.put(GITHUB_SHORTLINKS_API, headers=headers, json=update_data)
        return update_response.status_code == 200
    return False

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

# 🔹 Generate Random Short Code
def generate_short_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

# 🔹 Load Persistent Short Links
short_links = get_short_links()

# 🔹 Handle Direct APK Links (Only for Admins)
@bot.message_handler(func=lambda message: message.text.startswith("http"))
def handle_direct_link(message):
    user_id = message.chat.id

    if is_subscribed(user_id):
        original_link = message.text.strip()
        short_code = generate_short_code()
        short_links[short_code] = original_link
        update_short_links(short_links)
        short_link = f"https://t.me/{bot.get_me().username}?start=link_{short_code}"
        bot.send_message(message.chat.id, f"✅ Short link created: {short_link}")
    else:
        bot.send_message(message.chat.id, "❌ You must be a subscriber to generate links.")

# 🔹 Handle /start Command with AI Button
@bot.message_handler(commands=["start"])
def handle_start(message):
    text = message.text.strip()
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🤖 Ask AI", callback_data="ask_ai"))

    if text.startswith("/start link_"):
        short_code = text.replace("/start link_", "").strip()
        if short_code in short_links:
            user_id = message.chat.id
            original_link = short_links[short_code]

            if is_subscribed(user_id):
                bot.send_message(user_id, f"✅ **Here is your download link:**\n{original_link}", reply_markup=markup)
            else:
                bot.send_message(user_id, "❌ You must subscribe to get the APK.\nJoin here: https://t.me/skmods_000", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "❌ Invalid or expired link.", reply_markup=markup)
    else:
        messages = get_messages()
        bot.send_message(message.chat.id, messages["start"], reply_markup=markup)

# 🔹 Handle AI Button Click
@bot.callback_query_handler(func=lambda call: call.data == "ask_ai")
def handle_ai_button(call):
    bot.send_message(call.message.chat.id, "🤖 **Ask me anything!**\nUse `/ask <your question>`.")

# 🔹 Handle AI Queries
@bot.message_handler(commands=["ask"])
def handle_ask_command(message):
    bot.send_message(message.chat.id, "📝 **Ask me anything!**\nSend your question after `/ask`.")

@bot.message_handler(func=lambda message: message.text.startswith("/ask "))
def handle_ai_query(message):
    user_query = message.text.replace("/ask ", "").strip()

    if not user_query:
        bot.send_message(message.chat.id, "❌ Please provide a question after `/ask`.")
        return

    bot.send_message(message.chat.id, "⏳ Thinking...")  
    response = get_gemini_response(user_query)
    bot.send_message(message.chat.id, f"🤖 **AI Response:**\n{response}")

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
