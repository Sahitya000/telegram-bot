import telebot
import os

# Bot Token (Railway ke ENV me set karna)
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Hello! Bot is working! ✅")

bot.polling()
