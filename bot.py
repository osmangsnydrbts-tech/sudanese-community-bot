# -*- coding: utf-8 -*-

import os
import csv
import sqlite3
import logging
import sys
from datetime import datetime, date
from enum import Enum, auto
from typing import List, Dict, Optional
import re

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    PicklePersistence,
)

# =========================
# Configuration
# =========================

TOKEN = os.getenv("8342715370:AAGgUMEKd1E0u3hi_u28jMNrZA9RD0v0WXo")

if not TOKEN:
    print("❌ خطأ: لم يتم تعيين BOT_TOKEN في متغيرات البيئة")
    sys.exit(1)

ADMIN_USER = os.getenv("ADMIN_USER", "Osman")
ADMIN_PASS = os.getenv("ADMIN_PASS", "2580")

print("✅ تم تحميل التوكن بنجاح")

# =========================
# إعدادات التسجيل
# =========================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =========================
# حالات المحادثة
# =========================
class States(Enum):
    MAIN_MENU = auto()
    WAITING_FOR_CREDENTIALS = auto()
    ADMIN_PANEL = auto()
    # أضف باقي الحالات حسب احتياجك

# =========================
# دوال المعالجة
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء المحادثة"""
    user = update.message.from_user
    welcome_text = f"مرحباً {user.first_name}!\n\nمرحباً بك في بوت إدارة المصروفات."
    
    keyboard = [
        [KeyboardButton("تسجيل الدخول كمسؤول")],
        [KeyboardButton("المساعدة")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    return States.MAIN_MENU

async def handle_admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب تسجيل الدخول كمسؤول"""
    await update.message.reply_text("يرجى إرسال اسم المستخدم وكلمة المرور بالشكل التالي:\nusername:password")
    return States.WAITING_FOR_CREDENTIALS

async def handle_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة بيانات الاعتماد"""
    text = update.message.text.strip()
    
    if ":" in text:
        username, password = text.split(":", 1)
        username = username.strip()
        password = password.strip()
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            # تسجيل الدخول ناجح
            admin_keyboard = [
                [KeyboardButton("عرض الإحصائيات"), KeyboardButton("إضافة مصروف")],
                [KeyboardButton("تصدير البيانات"), KeyboardButton("العودة للرئيسية")]
            ]
            reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
            await update.message.reply_text("✅ تم تسجيل الدخول بنجاح كمسؤول!", reply_markup=reply_markup)
            return States.ADMIN_PANEL
        else:
            await update.message.reply_text("❌ بيانات الاعتماد غير صحيحة. حاول مرة أخرى.")
            return States.WAITING_FOR_CREDENTIALS
    else:
        await update.message.reply_text("❌ صيغة غير صحيحة. استخدم: username:password")
        return States.WAITING_FOR_CREDENTIALS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء المحادثة"""
    await update.message.reply_text("تم الإلغاء. ابدأ مرة أخرى باستخدام /start")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المساعدة"""
    help_text = """
🆘 **أوامر البوت:**

/start - بدء المحادثة
/help - عرض هذه المساعدة
/cancel - إلغاء العملية الحالية

**لوحة المسؤول:**
- تسجيل الدخول كمسؤول
- إدارة المصروفات
- عرض الإحصائيات
"""
    await update.message.reply_text(help_text)

# =========================
# الدالة الرئيسية
# =========================

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    
    # إنشاء Application بدلاً من Updater
    persistence = PicklePersistence(filepath="conversationbot")
    application = Application.builder().token(TOKEN).persistence(persistence).build()
    
    # إنشاء محادثة متقدمة
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.MAIN_MENU: [
                MessageHandler(filters.Regex("^تسجيل الدخول كمسؤول$"), handle_admin_login),
                MessageHandler(filters.Regex("^المساعدة$"), help_command),
            ],
            States.WAITING_FOR_CREDENTIALS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_credentials),
            ],
            States.ADMIN_PANEL: [
                # أضف معالجات لوحة المسؤول هنا
                MessageHandler(filters.Regex("^العودة للرئيسية$"), start),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('help', help_command)],
        name="expense_bot",
        persistent=True,
    )
    
    # إضافة المعالجات
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # بدء البوت
    print("🤖 بدء تشغيل بوت إدارة المصروفات...")
    application.run_polling()

if __name__ == '__main__':
    main()
