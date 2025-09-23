# test_bot.py
import os
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت يعمل!")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🚀 بدء التشغيل...")
    app.run_polling()

if __name__ == '__main__':
    main()
