# new_bot_fixed.py
import os
import logging
import sys

# ⚠️ تأكد من عدم استيراد أي شيء يتعلق بـ Updater
# استيراد مباشر وواضح فقط لـ Application

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ خطأ: لم يتم تعيين BOT_TOKEN في متغيرات البيئة")
    sys.exit(1)

print("✅ تم تحميل التوكن بنجاح")

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# استيراد المكتبات بعد التحقق من التوكن
try:
    from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ConversationHandler,
        filters,
        ContextTypes,
    )
    
    # تحقق أننا لا نستورد Updater عن طريق الخطأ
    if 'Updater' in dir():
        print("❌ خطأ: Updater مستورد عن طريق الخطأ!")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ خطأ في استيراد المكتبات: {e}")
    sys.exit(1)

# حالات المحادثة
class States:
    MAIN_MENU = 1
    WAITING_FOR_CREDENTIALS = 2
    ADMIN_PANEL = 3

# دوال المعالجة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    welcome_text = f"مرحباً {user.first_name}!\n\nمرحباً بك في بوت إدارة المصروفات."
    
    keyboard = [[KeyboardButton("تسجيل الدخول كمسؤول")], [KeyboardButton("المساعدة")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    return States.MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 للمساعدة اتصل بالدعم")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء")
    return ConversationHandler.END

def main():
    print("🔧 جاري إنشاء Application...")
    
    try:
        # إنشاء Application بشكل آمن
        application = Application.builder().token(TOKEN).build()
        
        # إضافة handlers بسيطة أولاً
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("cancel", cancel))
        
        print("✅ تم إنشاء Application بنجاح")
        print("🤖 بدء تشغيل البوت...")
        
        # التشغيل
        application.run_polling()
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # تحقق نهائي قبل التشغيل
    import telegram.ext as ext
    if hasattr(ext, 'Updater'):
        print("⚠️  تحذير: Updater موجود في telegram.ext، لكننا لا نستخدمه")
    
    main()
