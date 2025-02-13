import telebot
import os
import requests
import json
import threading
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

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, and GITHUB_TOKEN in Railway!")

bot = telebot.TeleBot(TOKEN)

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

# 

# 🔹 Get Short Links from GitHub


# 🔹 Get Short Links from GitHub


# 🔹 Get Short Links from GitHub

# 🔹 Fetch Short Links from GitHub
def get_short_links():
    try:
        response = requests.get(GITHUB_SHORTLINKS_API, timeout=5)
        response.raise_for_status()
        content_data = response.json()
        file_content = base64.b64decode(content_data["content"]).decode()
        return json.loads(file_content)
    except requests.RequestException:
        return {}

# 🔹 Update Short Links on GitHub
def update_short_links(new_data):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    response = requests.get(GITHUB_SHORTLINKS_API, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data.get("sha", "")

        update_data = {
            "message": "Updated Short Links",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }

        update_response = requests.put(GITHUB_SHORTLINKS_API, headers=headers, json=update_data)
        return update_response.status_code == 200
    return False

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

# 🔹 Generate Random Short Code
def generate_short_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

# 🔹 Load Persistent Short Links
short_links = get_short_links()

# 🔹 Handle Direct APK Links → Only Admins Can Send (Format: "link apk_name")
@bot.message_handler(func=lambda message: " " in message.text and message.text.startswith("http"))
def handle_direct_link(message):
    user_id = message.chat.id

    if is_admin(user_id):  # ✅ Only Admins Allowed
        parts = message.text.strip().split(" ", 1)
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Please provide APK link followed by its name.")
            return

        original_link, apk_name = parts
        short_code = generate_short_code()
        
        short_links[short_code] = {"link": original_link, "name": apk_name}

        if update_short_links(short_links):  # 🔄 Save Links to GitHub
            short_link = f"https://t.me/{bot.get_me().username}?start=link_{short_code}"
            bot.send_message(
                message.chat.id,
                f"✅ Short link created: {short_link}\n📌 APK Name: {apk_name}"
            )
        else:
            bot.send_message(message.chat.id, "❌ Failed to update short links on GitHub.")
    else:
        bot.send_message(message.chat.id, "❌ You are not allowed to send links.")

# 🔹 Handle Short Links for Users (Check Subscription & Give Link)
@bot.message_handler(func=lambda message: message.text.startswith("/start link_"))
def handle_short_link(message):
    short_code = message.text.split("_")[-1]
    apk_links = get_short_links()  # 🔄 GitHub se latest data fetch karein

    if short_code in apk_links:
        if is_subscribed(message.chat.id):
            apk_info = apk_links[short_code]
            bot.send_message(message.chat.id, f"{apk_info['name']}: {apk_info['link']}")  # ✅ Format: APKName: Link
        else:
            bot.send_message(message.chat.id, "❌ You must join the channel first to get the APK link.")
    else:
        bot.send_message(message.chat.id, "⚠️ Invalid or expired short link.")

# 🔹 Start the Bot

# 🔹 Start Bot

# 🔹 Start Bot

# 🔹 Bot Start


        #sahitya_app_link
        
@bot.message_handler(commands=["applist"])
def handle_applist(message):
    user_id = message.chat.id
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



    

# 🔹 Direct APK Name Input (Case-insensitive Matching)
@bot.message_handler(func=lambda message: True)
def handle_apk_request(message):
    user_id = message.chat.id
    apk_links = get_apk_links()

    app_name = message.text.strip().lower()  # 🔹 Case-insensitive comparison
    
    # 🔹 Match the APK name based on exact or substring match
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

    if update_short_links(apk_links):
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
