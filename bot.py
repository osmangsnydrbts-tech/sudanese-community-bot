# bot.py
import os
import sys
import logging

# التحقق من التوكن أولاً
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ خطأ: BOT_TOKEN غير معين")
    sys.exit(1)

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        # استيراد داخل الدالة لتجنب مشاكل الاستيراد المبكر
        from telegram.ext import Application, CommandHandler, ContextTypes
        from telegram import Update
        
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text("✅ البوت يعمل بنجاح!")
        
        # إنشاء Application
        application = Application.builder().token(TOKEN).build()
        
        # إضافة handlers
        application.add_handler(CommandHandler("start", start))
        
        logger.info("🤖 بدء تشغيل البوت...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ خطأ في التشغيل: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
