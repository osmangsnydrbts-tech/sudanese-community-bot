# -*- coding: utf-8 -*-

# حل لمشكلة imghdr
import sys
sys.modules['imghdr'] = type('imghdr', (), {'what': lambda *args, **kwargs: None})()

import os
import csv
import sqlite3
import logging
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
    CallbackContext,
    PicklePersistence,
)

# =========================
# Configuration
# =========================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ خطأ: لم يتم تعيين BOT_TOKEN في متغيرات البيئة")
    sys.exit(1)

ADMIN_USER = os.getenv("ADMIN_USER", "Osman")
ADMIN_PASS = os.getenv("ADMIN_PASS", "2580")

print("✅ تم تحميل التوكن بنجاح")

# ... (باقي الكود كما هو بدون تغيير)

def main():
    try:
        print("🚀 بدء تشغيل بوت الجالية السودانية...")
        
        if not TOKEN:
            print("❌ خطأ: لم يتم تعيين BOT_TOKEN")
            return
        
        # تهيئة التطبيق
        init_services_db()
        print("✅ تم تهيئة قاعدة البيانات")
        
        # إنشاء التطبيق
        persistence = PicklePersistence(filepath="conversationbot")
        application = Application.builder().token(TOKEN).persistence(persistence).build()
        
        # إضافة handlers مبسطة
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.Text(["📝 التسجيل"]), register_start))
        application.add_handler(MessageHandler(filters.Text(["📌 الخدمات"]), services_menu_start))
        application.add_handler(MessageHandler(filters.Text(["🔑 دخول"]), admin_login))
        
        print("✅ تم تحميل الـ handlers الأساسية")
        print("🤖 البوت جاهز للعمل...")
        
        # بدء البوت
        application.run_polling()
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
