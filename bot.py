import telebot
import os
import requests
import json
import time
import base64
import random
import string
import telebot.apihelper
from extra import send_subscription_message  # Importing function from extra.py


# 🔹 Environment Variables
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_ID_2 = os.getenv("CHANNEL_ID_2")  # Second Channel

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
TOKEN = os.getenv("BOT_TOKEN")

# 🔹 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"
GITHUB_SHORTLINKS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/short_links.json"
GITHUB_USERS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/users.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, and GITHUB_TOKEN in Railway!")

# 🔹 Initialize Bot
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
time.sleep(1)  # Wait for proper removal

# 🔹 Load Users from GitHub
def get_users():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(GITHUB_USERS_API, headers=headers)

    if response.status_code == 200:
        content_data = response.json()
        file_content = base64.b64decode(content_data["content"]).decode()
        return json.loads(file_content)
    return []  # 🔹 Always return a list

# 🔹 Update Users on GitHub
def update_users(new_users):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(GITHUB_USERS_API, headers=headers)

    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]

        update_data = {
            "message": "Updated Users List",
            "content": base64.b64encode(json.dumps(new_users, indent=4).encode()).decode(),
            "sha": sha
        }

        update_response = requests.put(GITHUB_USERS_API, headers=headers, json=update_data)
        return update_response.status_code in [200, 201]
    return False

# 🔹 Load Persistent Users List
users = get_users() or []  # Ensure users is always a list

# 🔹 /start Command
@bot.message_handler(commands=["join"])
def start(message):
    user_id = message.chat.id
    if user_id not in users:
        users.append(user_id)
        if update_users(users):
            bot.send_message(user_id, "✅ You have been added to the bot. Now you will receive channel updates!")
        else:
            bot.send_message(user_id, "❌ Failed to save your data. Please try again later.")
    else:
        bot.send_message(user_id, "📢 You are already in the bot system!")

# 🔹 Forward Channel Messages to Users

@bot.channel_post_handler(func=lambda message: True)
def forward_channel_message(message):
    for user_id in users:
        try:
            bot.forward_message(chat_id=user_id, from_chat_id=CHANNEL_ID, message_id=message.message_id)
        except Exception as e:
            print(f"❌ Error sending to {user_id}: {e}")


# 🔹 Load Messages from GitHub
def get_messages():
    try:
        response = requests.get(GITHUB_MESSAGES_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {
            "start": "👋 Welcome! Click below to download your app:",
            "subscribe": "❌ You must subscribe to both channels to get the APK. Join here:\n👉 https://t.me/sktech_000\n\n👉 https://t.me/instamaxpro",
            "update": "🔔 New APK Update Available: {app_name}\n📥 Download: {apk_link}"
        }

# 🔹 Get Short Links from GitHub
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
        sha = content_data["sha"]

        update_data = {
            "message": "Updated Short Links",
            "content": base64.b64encode(json.dumps(new_data, indent=4).encode()).decode(),
            "sha": sha
        }

        update_response = requests.put(GITHUB_SHORTLINKS_API, headers=headers, json=update_data)
        return update_response.status_code in [200, 201]
    return False

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
        chat_member1 = bot.get_chat_member(CHANNEL_ID, user_id)
        chat_member2 = bot.get_chat_member(CHANNEL_ID_2, user_id)
        return (
            chat_member1.status in ["member", "administrator", "creator"]
            and chat_member2.status in ["member", "administrator", "creator"]
        )
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

# 🔹 Handle Direct APK Links → Only Admins Can Send
@bot.message_handler(func=lambda message: 'http' in message.text)
def handle_direct_link(message):
    user_id = message.chat.id

    if is_admin(user_id):  # ✅ Only Admins Allowed
        original_message = message.text.strip()
        try:
            apk_name, original_link = original_message.split(' ', 1)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Please send the APK name followed by the link.")
            return

        short_code = generate_short_code()
        short_links[short_code] = {"name": apk_name, "link": original_link}
        if update_short_links(short_links):  # 🔄 Save Links to GitHub
            short_link = f"https://telegram.me/{bot.get_me().username}?start=link_{short_code}"
            bot.send_message(message.chat.id, f"✅ Short link created: {short_link}\n🔹 Name: {apk_name}")
        else:
            bot.send_message(message.chat.id, "❌ Failed to update short links on GitHub.")
    else:
        bot.send_message(message.chat.id, "❌ You are not allowed to send links.")

# 🔹 Handle Short Links for Users
@bot.message_handler(func=lambda message: message.text.startswith("/start link_"))
def handle_short_link(message):
    short_code = message.text.split("_")[-1]
    apk_links = get_short_links()  # 🔄 GitHub se latest data fetch karo

    if short_code in apk_links:
        apk_data = apk_links[short_code]
        if is_subscribed(message.chat.id):
            bot.send_message(message.chat.id, f"✅ Here is your APK link:\n🔹 Name: {apk_data['name']}\n🔹 Link: {apk_data['link']}")
        else:
            bot.send_message(message.chat.id, "You must subscribe to both channels to get the APK. Join here:\n👉 https://t.me/sktech_000\n\n👉 https://t.me/instamaxpro")
    else:
        bot.send_message(message.chat.id, "⚠️ Invalid or expired short link.")

# 🔹 Handle APK List Command
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

# 🔹 Ensure Links Never Expire
if __name__ == "__main__":
    bot.remove_webhook()  # Ensure webhook is removed
    time.sleep(1)  # Wait a moment before polling
    bot.infinity_polling(timeout=10, long_polling_timeout=5)  # More stable polling
