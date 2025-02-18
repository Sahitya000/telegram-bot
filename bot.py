import telebot
import os
import requests
import json
import time
import base64
import random
import string
import telebot.apihelper

# 👉 Environment Variables
CHANNEL_ID = os.getenv("CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
TOKEN = os.getenv("BOT_TOKEN")

# 👉 GitHub URLs
GITHUB_MESSAGES_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/messages.json"
GITHUB_APKS_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/apk_links.json"
GITHUB_REPO_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/apk_links.json"
GITHUB_SHORTLINKS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/short_links.json"
GITHUB_USERS_API = "https://api.github.com/repos/Sahitya000/telegram-bot/contents/users.json"

if not all([TOKEN, CHANNEL_ID, GITHUB_TOKEN]):
    raise ValueError("❌ ERROR: Please set BOT_TOKEN, CHANNEL_ID, and GITHUB_TOKEN in Railway!")

# 👉 Initialize Bot
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
time.sleep(1)  # Wait for proper removal

# 👉 Load Users from GitHub
def get_users():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(GITHUB_USERS_API, headers=headers)

    if response.status_code == 200:
        content_data = response.json()
        file_content = base64.b64decode(content_data["content"]).decode()
        return json.loads(file_content)
    return []

# 👉 Load Persistent Users List
users = get_users() or []

# 👉 Update Users List
def update_users(users):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(GITHUB_USERS_API, headers=headers)
    if response.status_code == 200:
        content_data = response.json()
        sha = content_data["sha"]
        update_data = {
            "message": "Updated Users List",
            "content": base64.b64encode(json.dumps(users, indent=4).encode()).decode(),
            "sha": sha
        }
        update_response = requests.put(GITHUB_USERS_API, headers=headers, json=update_data)
        return update_response.status_code in [200, 201]
    return False

# 👉 /start Command
@bot.message_handler(commands=["start"])
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

# 👉 Forward Messages from Channel
@bot.channel_post_handler(func=lambda message: True)
def forward_channel_message(message):
    global users
    users = get_users() or []  # Ensure latest users list is used
    
    for user_id in users:
        try:
            bot.forward_message(chat_id=user_id, from_chat_id=CHANNEL_ID, message_id=message.message_id)
        except telebot.apihelper.ApiTelegramException as e:
            if "bot was blocked by the user" in str(e) or "chat not found" in str(e):
                users.remove(user_id)  # Remove inactive users
                update_users(users)  # Save updated list
            print(f"❌ Error sending to {user_id}: {e}")

# 👉 Start Bot
if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=30, long_polling_timeout=25)
