import telebot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_buttons():
    keyboard = [
        [InlineKeyboardButton("📢 Join Telegram", url="https://t.me/skmods_000")],
        [InlineKeyboardButton("📸 Follow on Instagram", url="https://instagram.com/sahitya_000")]
    ]
    return InlineKeyboardMarkup(keyboard)

def send_subscription_message(bot, chat_id):
    message_text = (
        "❌ Sorry You have not subscribed SkMods channel And Instagram Account.\n\n"
        "Subscribe to the channel and Follow on Instagram.\n\n"
        "After done, come back for your link."
    )
    bot.send_message(chat_id=chat_id, text=message_text, reply_markup=get_buttons(), parse_mode="Markdown")

# Yahan aur extra features add kar sakte ho
