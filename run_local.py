import os
from bot import bot, init_db

if __name__ == "__main__":
    print("Initializing FPL Assistant Bot...")
    init_db()
    print("Bot is polling locally for updates... Press Ctrl+C to stop.")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
