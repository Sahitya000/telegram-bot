import telebot
import os

# GitHub Environment Variables se bot ka token aur links lena
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_LINK = os.getenv("GITHUB_LINK")
DRIVE_LINK = os.getenv("DRIVE_LINK")

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome! Send /apk to get the latest APK.")

@bot.message_handler(commands=['apk'])
def send_apk(message):
    bot.send_message(message.chat.id, f"🔗 GitHub: {GITHUB_LINK}\n🔗 Google Drive: {DRIVE_LINK}")

bot.polling()
