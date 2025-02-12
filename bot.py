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
@bot.message_handler(func=lambda message: message.text.startswith("http"))
def handle_direct_link(message):
    user_id = message.chat.id

    if is_admin(user_id):  # ✅ Only Admins Allowed
        original_link = message.text.strip()
        short_code = generate_short_code()
        short_links[short_code] = original_link
        update_short_links(short_links)  # 🔄 Save Links to GitHub
        short_link = f"https://t.me/{bot.get_me().username}?start=link_{short_code}"

        bot.send_message(message.chat.id, f"✅ Short link created: {short_link}")
    else:
        bot.send_message(message.chat.id, " You are not allowed to send links.❌")

# 🔹 Handle /start → Check Subscription for Short Links
@bot.message_handler(commands=["start"])
def handle_start(message):
    text = message.text.strip()

    if text.startswith("/start link_"):
        short_code = text.replace("/start link_", "").strip()

        if short_code in short_links:
            user_id = message.chat.id
            original_link = short_links[short_code]

            if is_subscribed(user_id):
                bot.send_message(user_id, f"✅ **Here is your download link:**\n{original_link}")
            else:
                bot.send_message(user_id, f" You must subscribe to get the APK.\nJoin here: https://t.me/skmods_000")
        else:
            bot.send_message(message.chat.id, "❌ Invalid or expired link.")
    else:
        messages = get_messages()
        bot.send_message(message.chat.id, messages["start"])
        
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
    matching_apk = next((key for key in apk_links if key.lower() == app_name), None)

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
        bot.send_message(user_id, "     ⚠️ Error ⚠️\n May be you entered wrong name of apk not available for this time try again later 😞\n send this message to @sks_000")

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


#sahitya_broadcast

# 🔹 GitHub Config File URL
GITHUB_CONFIG_URL = "https://raw.githubusercontent.com/Sahitya000/telegram-bot/main/config.json"

# 🔹 GitHub se config.json load karne ka function
def load_config():
    try:
        response = requests.get(GITHUB_CONFIG_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# 🔹 Config Load Karo
config = load_config()
ADMIN_ID = config.get("admin_id", 0)  # Default 0 agar na mile
GITHUB_USERS_URL = config.get("github_users_url", "")

bot = TeleBot(os.getenv("BOT_TOKEN"))  # Bot token environment se lo

# 🔹 Users.json load karne ka function
def load_users():
    try:
        response = requests.get(GITHUB_USERS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []

# 🔹 Bot start hone par user register ho
@bot.message_handler(commands=["start"])
def register_user(message):
    user_id = message.chat.id
    username = message.from_user.username or "No Username"
    name = message.from_user.first_name or "Unknown"

    users = load_users()

    # Check karo ki user already exist hai ya nahi
    if not any(u["id"] == user_id for u in users):
        users.append({"id": user_id, "name": name, "username": username})
        update_github_users(users)

    bot.reply_to(message, "✅ Bot activated! Ab aapko important updates milenge.")

# 🔹 GitHub users.json update function
def update_github_users(users):
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    update_data = {
        "message": "Updated user list",
        "content": base64.b64encode(json.dumps(users).encode()).decode(),
        "sha": get_github_file_sha(GITHUB_USERS_URL)
    }
    
    response = requests.put(GITHUB_USERS_URL.replace("raw.githubusercontent.com", "api.github.com/repos").replace("/main/", "/contents/"),
                            headers=headers, json=update_data)
    
    return response.status_code == 200

# 🔹 GitHub SHA fetch karne ka function
def get_github_file_sha(url):
    api_url = url.replace("raw.githubusercontent.com", "api.github.com/repos").replace("/main/", "/contents/")
    response = requests.get(api_url)
    return response.json().get("sha", "")

# 🔹 Broadcast message command (Sirf admin ke liye)
@bot.message_handler(commands=["broadcast"])
def broadcast_message(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⚠️ Sirf admin hi ye command use kar sakta hai!")
        return
    
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "⚠️ Broadcast ke liye message likhna zaroori hai!")
        return
    
    users = load_users()
    failed_count = 0

    for user in users:
        try:
            bot.send_message(user["id"], f"📢 **Broadcast Message:**\n{text}", parse_mode="Markdown")
            time.sleep(1)  # Rate limit avoid karne ke liye
        except Exception:
            failed_count += 1  # Agar user unavailable hai to count badhao

    bot.reply_to(message, f"✅ Broadcast completed!\n🚀 Total users: {len(users)}\n❌ Failed: {failed_count}")







print("🚀 Bot is running...")
bot.polling()







