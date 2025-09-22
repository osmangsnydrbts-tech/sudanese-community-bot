# -*- coding: utf-8 -*-



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

    ContextTypes,

    PicklePersistence,

)



# =========================

# Configuration

# =========================



TOKEN = os.getenv("BOT_TOKEN", "8342715370:AAGgUMEKd1E0u3hi_u28jMNrZA9RD0v0WXo")
ADMIN_USER = os.getenv("ADMIN_USER", "Osman")
ADMIN_PASS = os.getenv("ADMIN_PASS", "2580")



# ملفات CSV

MEMBERS_FILE = "members.csv"

USERS_FILE = "users.csv"

DELIVERIES_FILE = "deliveries.csv"

ASSISTANTS_FILE = "assistants.csv"

STATISTICS_FILE = "statistics_report.csv"

SERVICE_REQUESTS_CSV = "services_requests.csv"



# قاعدة البيانات للخدمات

SERVICES_DB = "services.db"



# مجلد ملفات CSV للخدمات

SERVICES_CSV_DIR = "services_csv"



# =========================

# States using Enum

# =========================



class States(Enum):

    # Registration

    ASK_NAME = auto()

    ASK_PASSPORT = auto()

    ASK_PHONE = auto()

    ASK_ADDRESS = auto()

    ASK_ROLE = auto()

    ASK_FAMILY_MEMBERS = auto()

    

    # Admin states

    ADMIN_USER_INPUT = auto()

    ADMIN_PASS_INPUT = auto()

    ADMIN_MENU = auto()

    ACCOUNT_MANAGEMENT = auto()

    MANAGE_ASSISTANTS = auto()

    CREATE_ASSISTANT_USER = auto()

    CREATE_ASSISTANT_PASS = auto()

    DELETE_ASSISTANT = auto()

    CHANGE_ASSISTANT_USER = auto()

    CHANGE_ASSISTANT_PASS = auto()

    DELETE_ASSISTANT_REPORTS = auto()

    

    # Members data management

    MANAGE_MEMBERS_DATA = auto()

    CONFIRM_DELETE_MEMBERS = auto()

    

    # Delivery reports

    MANAGE_DELIVERY_REPORTS = auto()

    CONFIRM_DELETE_DELIVERIES = auto()

    

    # Assistant states

    ASSISTANT_MENU = auto()

    RECORD_DELIVERY_PASSPORT = auto()

    CONFIRM_DELIVERY = auto()

    ASSISTANT_VIEW_DELIVERIES = auto()

    

    # Statistics

    STATS_MENU = auto()

    CONFIRM_DELETE_STATS = auto()

    

    # Services

    SERVICES_MENU = auto()

    SERVICE_CONFIRM = auto()

    SERVICE_PASSPORT = auto()

    

    # Admin services management

    MANAGE_SERVICES = auto()

    ADD_SERVICE = auto()

    DELETE_SERVICE = auto()

    SERVICE_REPORT = auto()

    SERVICE_REPORT_CHOICE = auto()

    DELETE_SERVICE_REPORT = auto()

    CONFIRM_DELETE_SERVICE_REPORT = auto()

    SELECT_SERVICE_FOR_REPORT = auto()

    SELECT_SERVICE_FOR_DELETE = auto()

    CONFIRM_DELETE_SINGLE_SERVICE = auto()

    

    # Broadcast

    BROADCAST_MESSAGE = auto()



# =========================

# Logging

# =========================



logging.basicConfig(

    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",

    level=logging.INFO

)

logger = logging.getLogger(__name__)



# =========================

# CSV Helper functions

# =========================



def ensure_csv(filename: str, header: List[str]) -> None:

    """Create file with header if not exists or empty."""

    if not os.path.exists(filename) or os.stat(filename).st_size == 0:

        with open(filename, "w", newline="", encoding="utf-8") as f:

            writer = csv.writer(f)

            writer.writerow(header)



def read_csv_file(filename: str) -> List[Dict[str, str]]:

    if not os.path.exists(filename):

        return []

    with open(filename, "r", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        return list(reader)



def write_csv_file(filename: str, data: List[Dict[str, str]], fieldnames: List[str]) -> None:

    with open(filename, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()

        writer.writerows(data)



def append_csv_row(filename: str, row: Dict[str, str], fieldnames: List[str]) -> None:

    file_exists = os.path.isfile(filename) and os.stat(filename).st_size > 0

    with open(filename, "a", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:

            writer.writeheader()

        writer.writerow(row)



def count_csv_rows(filename: str) -> int:

    if not os.path.exists(filename):

        return 0

    with open(filename, newline="", encoding="utf-8") as f:

        reader = csv.reader(f)

        return max(0, sum(1 for _ in reader) - 1)



# إنشاء مجلد CSV للخدمات

os.makedirs(SERVICES_CSV_DIR, exist_ok=True)



# تأكد من وجود ملفات CSV

ensure_csv(MEMBERS_FILE, ["الاسم", "الجواز", "الهاتف", "العنوان", "الصفة", "عدد_افراد_الاسرة"])

ensure_csv(ASSISTANTS_FILE, ["username", "password"])

ensure_csv(DELIVERIES_FILE, ["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"])

ensure_csv(USERS_FILE, ["user_id", "username"])

ensure_csv(SERVICE_REQUESTS_CSV, ["رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"])



# =========================

# Database (SQLite) for services & requests

# =========================



def init_services_db():

    conn = sqlite3.connect(SERVICES_DB)

    cursor = conn.cursor()

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS services (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE

        )

    """)

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS service_requests (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            passport TEXT,

            service_name TEXT,

            request_date TEXT,

            requester TEXT

        )

    """)

    conn.commit()

    conn.close()



def add_service_to_db(service_name: str) -> bool:

    try:

        conn = sqlite3.connect(SERVICES_DB)

        cursor = conn.cursor()

        cursor.execute("INSERT INTO services (name) VALUES (?)", (service_name,))

        conn.commit()

        conn.close()

        

        # إنشاء ملف CSV منفصل للخدمة

        service_csv_file = os.path.join(SERVICES_CSV_DIR, f"{service_name}.csv")

        ensure_csv(service_csv_file, ["رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"])

        

        return True

    except sqlite3.IntegrityError:

        return False

    except Exception:

        logger.exception("Error adding service to DB")

        return False



def delete_service_from_db(service_name: str) -> bool:

    try:

        conn = sqlite3.connect(SERVICES_DB)

        cursor = conn.cursor()

        

        # حذف الخدمة من جدول الخدمات

        cursor.execute("DELETE FROM services WHERE name = ?", (service_name,))

        deleted = cursor.rowcount

        

        # حذف جميع طلبات هذه الخدمة

        cursor.execute("DELETE FROM service_requests WHERE service_name = ?", (service_name,))

        

        conn.commit()

        conn.close()

        

        # حذف ملف CSV الخاص بالخدمة

        service_csv_file = os.path.join(SERVICES_CSV_DIR, f"{service_name}.csv")

        if os.path.exists(service_csv_file):

            os.remove(service_csv_file)

        

        return deleted > 0

    except Exception:

        logger.exception("Error deleting service from DB")

        return False



def get_services_from_db() -> List[Dict[str, str]]:

    conn = sqlite3.connect(SERVICES_DB)

    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM services ORDER BY id")

    rows = cursor.fetchall()

    conn.close()

    return [{"service_id": str(r[0]), "service_name": r[1]} for r in rows]



def add_service_request(passport: str, service_name: str, requester: str):

    try:

        conn = sqlite3.connect(SERVICES_DB)

        cursor = conn.cursor()

        request_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        cursor.execute("""

            INSERT INTO service_requests (passport, service_name, request_date, requester)

            VALUES (?, ?, ?, ?)

        """, (passport, service_name, request_date, requester))

        conn.commit()

        conn.close()

        

        # إضافة الطلب إلى ملف CSV الخاص بالخدمة

        service_csv_file = os.path.join(SERVICES_CSV_DIR, f"{service_name}.csv")

        append_csv_row(service_csv_file, {

            "رقم_الجواز": passport,

            "الخدمة": service_name,

            "تاريخ_الطلب": request_date,

            "مقدم_الطلب": requester

        }, ["رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"])

        

    except Exception:

        logger.exception("Error inserting service request")



def get_service_requests_from_db():

    conn = sqlite3.connect(SERVICES_DB)

    cursor = conn.cursor()

    cursor.execute("SELECT id, passport, service_name, request_date, requester FROM service_requests ORDER BY id")

    rows = cursor.fetchall()

    conn.close()

    return rows



def get_service_requests_by_service(service_name: str = None):

    conn = sqlite3.connect(SERVICES_DB)

    cursor = conn.cursor()

    

    if service_name:

        cursor.execute("""

            SELECT id, passport, service_name, request_date, requester 

            FROM service_requests 

            WHERE service_name = ?

            ORDER BY id

        """, (service_name,))

    else:

        cursor.execute("""

            SELECT id, passport, service_name, request_date, requester 

            FROM service_requests 

            ORDER BY id

        """)

    

    rows = cursor.fetchall()

    conn.close()

    return rows



def delete_service_request(request_id: int) -> bool:

    try:

        conn = sqlite3.connect(SERVICES_DB)

        cursor = conn.cursor()

        cursor.execute("DELETE FROM service_requests WHERE id = ?", (request_id,))

        deleted = cursor.rowcount

        conn.commit()

        conn.close()

        return deleted > 0

    except Exception:

        logger.exception("Error deleting service request from DB")

        return False



def delete_all_service_requests() -> bool:

    try:

        conn = sqlite3.connect(SERVICES_DB)

        cursor = conn.cursor()

        cursor.execute("DELETE FROM service_requests")

        conn.commit()

        conn.close()

        

        # حذف جميع ملفات CSV للخدمات وإعادة إنشائها فارغة

        services = get_services_from_db()

        for service in services:

            service_csv_file = os.path.join(SERVICES_CSV_DIR, f"{service['service_name']}.csv")

            if os.path.exists(service_csv_file):

                os.remove(service_csv_file)

            ensure_csv(service_csv_file, ["رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"])

        

        return True

    except Exception:

        logger.exception("Error deleting all service requests from DB")

        return False



def delete_service_requests_by_service(service_name: str) -> bool:

    try:

        conn = sqlite3.connect(SERVICES_DB)

        cursor = conn.cursor()

        cursor.execute("DELETE FROM service_requests WHERE service_name = ?", (service_name,))

        deleted = cursor.rowcount

        conn.commit()

        conn.close()

        

        # إعادة إنشاء ملف CSV الخاص بالخدمة فارغ

        service_csv_file = os.path.join(SERVICES_CSV_DIR, f"{service_name}.csv")

        if os.path.exists(service_csv_file):

            os.remove(service_csv_file)

        ensure_csv(service_csv_file, ["رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"])

        

        return deleted > 0

    except Exception:

        logger.exception("Error deleting service requests by service")

        return False



def check_existing_service_request(passport: str, service_name: str) -> bool:

    """Check if a service request already exists for this passport and service"""

    conn = sqlite3.connect(SERVICES_DB)

    cursor = conn.cursor()

    cursor.execute("""

        SELECT COUNT(*) FROM service_requests 

        WHERE passport = ? AND service_name = ?

    """, (passport, service_name))

    count = cursor.fetchone()[0]

    conn.close()

    return count > 0



def is_passport_registered(passport: str) -> bool:

    """Check if passport is already registered in members.csv"""

    members = read_csv_file(MEMBERS_FILE)

    return any(m.get("الجواز") == passport for m in members)



def get_member_by_passport(passport: str) -> Optional[Dict[str, str]]:

    """Get member details by passport number"""

    members = read_csv_file(MEMBERS_FILE)

    for member in members:

        if member.get("الجواز") == passport:

            return member

    return None



def check_existing_delivery(passport: str) -> Optional[Dict[str, str]]:

    """Check if a delivery already exists for this passport"""

    deliveries = read_csv_file(DELIVERIES_FILE)

    for delivery in deliveries:

        if delivery.get("رقم_الجواز") == passport:

            return delivery

    return None



def get_service_statistics() -> Dict[str, int]:

    """إحصائيات الخدمات"""

    services = get_services_from_db()

    stats = {}

    

    for service in services:

        service_name = service["service_name"]

        conn = sqlite3.connect(SERVICES_DB)

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM service_requests WHERE service_name = ?", (service_name,))

        count = cursor.fetchone()[0]

        conn.close()

        stats[service_name] = count

    

    return stats



# =========================

# Keyboards

# =========================



def main_menu_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("📝 التسجيل"), KeyboardButton("📌 الخدمات")],

            [KeyboardButton("ℹ️ عن المنصة"), KeyboardButton("📞 تواصل معنا")],

            [KeyboardButton("❌ إلغاء")],

        ],

        resize_keyboard=True,

    )



def admin_login_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("🔑 دخول")],

            [KeyboardButton("❌ إلغاء")],

        ],

        resize_keyboard=True,

    )



def contact_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("📞 الهاتف"), KeyboardButton("✉️ البريد الإلكتروني")],

            [KeyboardButton("📱 واتساب"), KeyboardButton("📘 فيسبوك")],

            [KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def admin_menu_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("👥 إدارة الحسابات"), KeyboardButton("📊 الإحصائيات")],

            [KeyboardButton("📋 كشوفات التسليم"), KeyboardButton("👷 إدارة الخدمات")],

            [KeyboardButton("📢 إرسال رسالة للكل"), KeyboardButton("🚪 تسجيل خروج")],

        ],

        resize_keyboard=True,

    )



def account_management_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("👮 إدارة المشرفين"), KeyboardButton("👥 بيانات المسجلين")],

            [KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def manage_members_data_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("⬇️ تنزيل البيانات"), KeyboardButton("🗑️ مسح البيانات")],

            [KeyboardButton("📊 ملخص المسجلين"), KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def assistant_menu_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("📦 تسجيل تسليم"), KeyboardButton("📋 كشوفات التسليم")],

            [KeyboardButton("🚪 تسجيل خروج")],

        ],

        resize_keyboard=True,

    )



def assistants_management_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("➕ إضافة مشرف"), KeyboardButton("🗑️ حذف مشرف")],

            [KeyboardButton("🔑 تغيير كلمة المرور"), KeyboardButton("📋 كشف المشرفين")],

            [KeyboardButton("📥 تنزيل قائمة المشرفين"), KeyboardButton("🗑️ حذف كشوفات مشرف")],

            [KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def delivery_reports_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("⬇️ تنزيل الكشوفات"), KeyboardButton("🗑️ حذف الكشوفات")],

            [KeyboardButton("📊 عرض الملخص"), KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def assistant_delivery_reports_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("📥 تحميل"), KeyboardButton("📊 ملخص")],

            [KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def confirm_delivery_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("✅ نعم - تأكيد"), KeyboardButton("❌ لا - إلغاء")],

        ],

        resize_keyboard=True,

    )



def stats_choice_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("📋 عرض الملخص"), KeyboardButton("📥 تنزيل تقرير CSV")],

            [KeyboardButton("🗑️ حذف الملخص"), KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def confirm_delete_kb():

    return ReplyKeyboardMarkup(

        [[KeyboardButton("✅ نعم، احذف الكشوفات")],

         [KeyboardButton("❌ لا، إلغاء")]],

        resize_keyboard=True,

    )



def confirm_delete_members_kb():

    return ReplyKeyboardMarkup(

        [[KeyboardButton("✅ نعم، احذف بيانات المسجلين")],

         [KeyboardButton("❌ لا، إلغاء")]],

        resize_keyboard=True,

    )



def confirm_delete_stats_kb():

    return ReplyKeyboardMarkup(

        [[KeyboardButton("✅ نعم، احذف الملخص")],

         [KeyboardButton("❌ لا، إلغاء")]],

        resize_keyboard=True,

    )



def cancel_or_back_kb():

    return ReplyKeyboardMarkup(

        [[KeyboardButton("❌ إلغاء"), KeyboardButton("🔙 رجوع")]], 

        resize_keyboard=True

    )



def services_admin_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("➕ إضافة خدمة"), KeyboardButton("📋 عرض الخدمات")],

            [KeyboardButton("🗑️ حذف خدمة"), KeyboardButton("📊 إحصائيات الخدمات")],

            [KeyboardButton("📄 كشف الخدمات"), KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def service_report_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("📄 كشف لخدمة واحدة"), KeyboardButton("📄 كشف لكل الخدمات")],

            [KeyboardButton("🗑️ حذف كشوف الخدمات"), KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def service_delete_report_kb():

    return ReplyKeyboardMarkup(

        [

            [KeyboardButton("🗑️ حذف كشف خدمة واحدة"), KeyboardButton("🗑️ حذف كل الكشوفات")],

            [KeyboardButton("🔙 رجوع")],

        ],

        resize_keyboard=True,

    )



def confirm_delete_service_kb():

    return ReplyKeyboardMarkup(

        [[KeyboardButton("✅ نعم، احذف كشف الخدمة")],

         [KeyboardButton("❌ لا، إلغاء")]],

        resize_keyboard=True,

    )



def services_menu_kb(services):

    keyboard = []

    for service in services:

        keyboard.append([KeyboardButton(service["service_name"])])

    keyboard.append([KeyboardButton("🔙 رجوع")])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



def services_selection_kb(services):

    keyboard = []

    for service in services:

        keyboard.append([KeyboardButton(service["service_name"])])

    keyboard.append([KeyboardButton("🔙 رجوع")])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



# =========================

# Utility functions

# =========================



def add_user_if_not_exists(user_id: int, username: str):

    users = read_csv_file(USERS_FILE)

    if not any(u.get("user_id") == str(user_id) for u in users):

        append_csv_row(USERS_FILE, {"user_id": str(user_id), "username": username or ""}, ["user_id", "username"])



def validate_admin_session(context: ContextTypes.DEFAULT_TYPE) -> bool:

    user_type = context.user_data.get("user_type")

    login_user = context.user_data.get("login_user")

    if not user_type or not login_user:

        return False

    if user_type == "main_admin":

        return login_user == ADMIN_USER

    if user_type == "assistant":

        assistants = read_csv_file(ASSISTANTS_FILE)

        return any(row.get("username") == login_user for row in assistants)

    return False



def format_phone_number(phone: str) -> str:

    """Format phone number for WhatsApp link"""

    cleaned = re.sub(r'\D', '', phone)

    if cleaned.startswith('00'):

        cleaned = cleaned[2:]

    elif cleaned.startswith('0'):

        cleaned = '20' + cleaned[1:]

    return cleaned



# =========================

# Handlers

# =========================



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user_if_not_exists(user.id, user.username or "")

    

    welcome_message = (

        "مرحباً بك في بوت الجالية السودانية بأسوان 🇸🇩\n\n"

        "يسعدنا انضمامك إلى منصّتنا التي وُجدت لخدمة جميع أبناء الجالية، "

        "وتنظيم بياناتهم وتسهيل الوصول إلى الخدمات."

    )

    

    await update.message.reply_text(welcome_message, reply_markup=main_menu_kb())

    return ConversationHandler.END



async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("⬅️ رجعت للقائمة الرئيسية.", reply_markup=main_menu_kb())

    return ConversationHandler.END



async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):

    about_text = (

        "ℹ️ من نحن:\n\n"

        "نحن الجالية السودانية في أسوان، كيان اجتماعي وتنظيمي يعمل على ربط أفراد الجالية ببعضهم البعض، "

        "وتقديم الدعم والخدمات اللازمة لهم في مجالات التعليم، الصحة، العمل، والقضايا الاجتماعية.\n\n"

        "انطلقنا من إيماننا بدور الجالية في بناء جسور تعاون بين السودان ومصر، "

        "وتعزيز قيم التكافل والمسؤولية المشتركة."

    )

    await update.message.reply_text(about_text, reply_markup=main_menu_kb())



async def contact_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("📞 اختر وسيلة التواصل:", reply_markup=contact_kb())



async def contact_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("☎️ رقم الاتصال: 00201000098572\n(متاح للاتصال خلال ساعات النهار)", reply_markup=contact_kb())



async def contact_email(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("📧 البريد: shareef@sudanaswan.com\nسوف نرد خلال 24 ساعة", reply_markup=contact_kb())



async def contact_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):

    phone = format_phone_number("00201000098572")

    whatsapp_link = f"https://wa.me/{phone}"

    await update.message.reply_text(f"📱 واتساب: [اضغط هنا للتواصل عبر واتساب]({whatsapp_link})", 

                                   parse_mode="Markdown", reply_markup=contact_kb())



async def contact_facebook(update: Update, context: ContextTypes.DEFAULT_TYPE):

    facebook_link = "https://www.facebook.com/share/1CSfqcbtid/"

    await update.message.reply_text(f"📘 فيسبوك: [اضغط هنا لزيارة صفحتنا على فيسبوك]({facebook_link})", 

                                   parse_mode="Markdown", reply_markup=contact_kb())



async def contact_back(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await go_main_menu(update, context)



async def show_admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """عرض خيار دخول الأدمن عند استلام علامة @"""

    if "@" in update.message.text:

        await update.message.reply_text("🔐 اختر خيار الدخول:", reply_markup=admin_login_kb())

    else:

        await update.message.reply_text("⬅️ رجعت للقائمة الرئيسية.", reply_markup=main_menu_kb())



# =========================

# Registration flow

# =========================



async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("✍️ أدخل اسمك الثلاثي:", reply_markup=cancel_or_back_kb())

    return States.ASK_NAME



async def ask_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):

    name = update.message.text.strip()

    if name in ("🔙 رجوع", "❌ إلغاء"):

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    context.user_data["name"] = name

    await update.message.reply_text("🛂 أدخل رقم الجواز:", reply_markup=cancel_or_back_kb())

    return States.ASK_PASSPORT



async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    passport = update.message.text.strip()

    if passport == "🔙 رجوع":

        await update.message.reply_text("✍️ أدخل اسمك الثلاثي:", reply_markup=cancel_or_back_kb())

        return States.ASK_NAME

    if passport == "❌ إلغاء":

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    if is_passport_registered(passport):

        await update.message.reply_text(

            "⚠️ أنت مسجل بالفعل في النظام.\n"

            "يمكنك استخدام قائمة الخدمات لطلب خدمات أخرى.",

            reply_markup=main_menu_kb()

        )

        context.user_data.clear()

        return ConversationHandler.END

    

    context.user_data["passport"] = passport

    await update.message.reply_text("📞 أدخل رقم الهاتف:", reply_markup=cancel_or_back_kb())

    return States.ASK_PHONE



async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):

    phone = update.message.text.strip()

    if phone == "🔙 رجوع":

        await update.message.reply_text("🛂 أدخل رقم الجواز:", reply_markup=cancel_or_back_kb())

        return States.ASK_PASSPORT

    if phone == "❌ إلغاء":

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    context.user_data["phone"] = phone

    await update.message.reply_text("🏠 أدخل عنوان السكن:", reply_markup=cancel_or_back_kb())

    return States.ASK_ADDRESS



async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE):

    address = update.message.text.strip()

    if address == "🔙 رجوع":

        await update.message.reply_text("📞 أدخل رقم الهاتف:", reply_markup=cancel_or_back_kb())

        return States.ASK_PHONE

    if address == "❌ إلغاء":

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    context.user_data["address"] = address

    await update.message.reply_text("👤 أدخل صفتك (مثال: رب أسرة، طالب، إلخ):", reply_markup=cancel_or_back_kb())

    return States.ASK_ROLE



async def ask_family_members(update: Update, context: ContextTypes.DEFAULT_TYPE):

    role = update.message.text.strip()

    if role == "🔙 رجوع":

        await update.message.reply_text("🏠 أدخل عنوان السكن:", reply_markup=cancel_or_back_kb())

        return States.ASK_ADDRESS

    if role == "❌ إلغاء":

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    context.user_data["role"] = role

    await update.message.reply_text("👨‍👩‍👧‍👦 أدخل عدد أفراد الأسرة (رقم فقط):", reply_markup=cancel_or_back_kb())

    return States.ASK_FAMILY_MEMBERS



async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):

    family_members = update.message.text.strip()

    if family_members == "🔙 رجوع":

        await update.message.reply_text("👤 أدخل صفتك (مثال: رب أسرة، طالب، إلخ):", reply_markup=cancel_or_back_kb())

        return States.ASK_ROLE

    if family_members == "❌ إلغاء":

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    try:

        family_count = int(family_members)

        if family_count < 1:

            await update.message.reply_text("⚠️ يجب أن يكون عدد أفراد الأسرة أكثر من صفر. أعد إدخال العدد:", reply_markup=cancel_or_back_kb())

            return States.ASK_FAMILY_MEMBERS

    except ValueError:

        await update.message.reply_text("⚠️ يجب إدخال رقم صحيح. أعد إدخال عدد أفراد الأسرة:", reply_markup=cancel_or_back_kb())

        return States.ASK_FAMILY_MEMBERS

    

    name = context.user_data.get("name")

    passport = context.user_data.get("passport")

    phone = context.user_data.get("phone")

    address = context.user_data.get("address")

    role = context.user_data.get("role")

    

    append_csv_row(

        MEMBERS_FILE,

        {

            "الاسم": name,

            "الجواز": passport,

            "الهاتف": phone,

            "العنوان": address,

            "الصفة": role,

            "عدد_افراد_الاسرة": str(family_count)

        },

        ["الاسم", "الجواز", "الهاتف", "العنوان", "الصفة", "عدد_افراد_الاسرة"]

    )

    

    await update.message.reply_text(

        "✅ تم تسجيل بياناتك بنجاح!\n"

        "شكراً لانضمامك إلى منصة الجالية السودانية بأسوان.",

        reply_markup=main_menu_kb()

    )

    

    context.user_data.clear()

    return ConversationHandler.END



async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await go_main_menu(update, context)

    context.user_data.clear()

    return ConversationHandler.END



# =========================

# Admin login and menus

# =========================



async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("👤 أدخل اسم المستخدم:", reply_markup=cancel_or_back_kb())

    return States.ADMIN_USER_INPUT



async def admin_get_user(update: Update, context: ContextTypes.DEFAULT_TYPE):

    username = update.message.text.strip()

    if username in ("🔙 رجوع", "❌ إلغاء"):

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    context.user_data["login_user_temp"] = username

    await update.message.reply_text("🔐 أدخل كلمة المرور:", reply_markup=cancel_or_back_kb())

    return States.ADMIN_PASS_INPUT



async def admin_get_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):

    password = update.message.text.strip()

    username = context.user_data.get("login_user_temp")

    

    if password in ("🔙 رجوع", "❌ إلغاء"):

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    if username == ADMIN_USER and password == ADMIN_PASS:

        context.user_data["login_user"] = username

        context.user_data["user_type"] = "main_admin"

        await update.message.reply_text("✅ تم الدخول كمسؤول رئيسي.", reply_markup=admin_menu_kb())

        return States.ADMIN_MENU

    

    assistants = read_csv_file(ASSISTANTS_FILE)

    for assistant in assistants:

        if assistant.get("username") == username and assistant.get("password") == password:

            context.user_data["login_user"] = username

            context.user_data["user_type"] = "assistant"

            await update.message.reply_text("✅ تم الدخول كمشرف.", reply_markup=assistant_menu_kb())

            return States.ASSISTANT_MENU

    

    await update.message.reply_text("❌ بيانات الدخول غير صحيحة.", reply_markup=main_menu_kb())

    return ConversationHandler.END



async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context):

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    user_type = context.user_data.get("user_type")

    

    if text == "👥 إدارة الحسابات":

        if user_type == "main_admin":

            await update.message.reply_text("👥 إدارة الحسابات:", reply_markup=account_management_kb())

            return States.ACCOUNT_MANAGEMENT

        else:

            await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=assistant_menu_kb())

    

    elif text == "📊 الإحصائيات":

        if user_type == "main_admin":

            await update.message.reply_text("📊 اختر نوع الإحصائيات:", reply_markup=stats_choice_kb())

            return States.STATS_MENU

        else:

            await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=assistant_menu_kb())

    

    elif text == "📋 كشوفات التسليم":

        if user_type == "main_admin":

            await update.message.reply_text("📋 إدارة كشوفات التسليم:", reply_markup=delivery_reports_kb())

            return States.MANAGE_DELIVERY_REPORTS

        elif user_type == "assistant":

            await update.message.reply_text("📋 اختر نوع الكشف:", reply_markup=assistant_delivery_reports_kb())

            return States.ASSISTANT_VIEW_DELIVERIES

    

    elif text == "👷 إدارة الخدمات":

        if user_type == "main_admin":

            await update.message.reply_text("👷 إدارة الخدمات:", reply_markup=services_admin_kb())

            return States.MANAGE_SERVICES

        else:

            await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=assistant_menu_kb())

    

    elif text == "📢 إرسال رسالة للكل":

        if user_type == "main_admin":

            await update.message.reply_text("📢 أدخل الرسالة التي تريد إرسالها للجميع:", reply_markup=cancel_or_back_kb())

            return States.BROADCAST_MESSAGE

        else:

            await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=assistant_menu_kb())

    

    elif text == "📦 تسجيل تسليم":

        if user_type == "assistant":

            await update.message.reply_text("🛂 أدخل رقم جواز العضو:", reply_markup=cancel_or_back_kb())

            return States.RECORD_DELIVERY_PASSPORT

        else:

            await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=admin_menu_kb())

    

    elif text == "🚪 تسجيل خروج":

        context.user_data.pop("login_user", None)

        context.user_data.pop("user_type", None)

        await update.message.reply_text("🚪 تم تسجيل الخروج.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    return States.ADMIN_MENU if user_type == "main_admin" else States.ASSISTANT_MENU



async def account_management_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    

    if text == "👮 إدارة المشرفين":

        await update.message.reply_text("👮 إدارة المشرفين:", reply_markup=assistants_management_kb())

        return States.MANAGE_ASSISTANTS

    

    elif text == "👥 بيانات المسجلين":

        await update.message.reply_text("👥 إدارة بيانات المسجلين:", reply_markup=manage_members_data_kb())

        return States.MANAGE_MEMBERS_DATA

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت للقائمة الرئيسية للأدمن.", reply_markup=admin_menu_kb())

        return States.ADMIN_MENU

    

    return States.ACCOUNT_MANAGEMENT



async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    message = update.message.text

    if message in ("🔙 رجوع", "❌ إلغاء"):

        await update.message.reply_text("❌ تم إلغاء الإرسال.", reply_markup=admin_menu_kb())

        return States.ADMIN_MENU

    

    users = read_csv_file(USERS_FILE)

    success = 0

    failed = 0

    

    for user in users:

        try:

            await context.bot.send_message(chat_id=user["user_id"], text=message)

            success += 1

        except Exception as e:

            logger.error(f"Failed to send message to {user['user_id']}: {e}")

            failed += 1

    

    await update.message.reply_text(

        f"✅ تم إرسال الرسالة:\n"

        f"✅ نجح: {success}\n"

        f"❌ فشل: {failed}",

        reply_markup=admin_menu_kb()

    )

    return States.ADMIN_MENU



# =========================

# Services: admin side

# =========================



async def manage_services_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":

        await update.message.reply_text("⚠️ ليس لديك صلاحيات للوصول لإدارة الخدمات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    

    if text == "➕ إضافة خدمة":

        await update.message.reply_text("📝 أدخل اسم الخدمة الجديدة:", reply_markup=cancel_or_back_kb())

        return States.ADD_SERVICE

    

    elif text == "📋 عرض الخدمات":

        services = get_services_from_db()

        if not services:

            await update.message.reply_text("⚠️ لا توجد خدمات مضافة.", reply_markup=services_admin_kb())

            return States.MANAGE_SERVICES

        

        report = "📋 قائمة الخدمات:\n\n"

        for i, service in enumerate(services, 1):

            report += f"{i}. {service['service_name']}\n"

        

        await update.message.reply_text(report, reply_markup=services_admin_kb())

        return States.MANAGE_SERVICES

    

    elif text == "🗑️ حذف خدمة":

        services = get_services_from_db()

        if not services:

            await update.message.reply_text("⚠️ لا توجد خدمات مضافة.", reply_markup=services_admin_kb())

            return States.MANAGE_SERVICES

        

        keyboard = [[KeyboardButton(s["service_name"])] for s in services]

        keyboard.append([KeyboardButton("🔙 رجوع")])

        await update.message.reply_text(

            "📋 اختر الخدمة للحذف:",

            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        )

        return States.DELETE_SERVICE

    

    elif text == "📊 إحصائيات الخدمات":

        services_stats = get_service_statistics()

        services = get_services_from_db()

        

        if not services:

            await update.message.reply_text("⚠️ لا توجد خدمات مضافة.", reply_markup=services_admin_kb())

            return States.MANAGE_SERVICES

        

        report = "📊 إحصائيات الخدمات:\n\n"

        total_requests = 0

        

        for service in services:

            service_name = service["service_name"]

            requests_count = services_stats.get(service_name, 0)

            total_requests += requests_count

            report += f"🔹 {service_name}: {requests_count} طلب\n"

        

        report += f"\n📋 إجمالي الطلبات: {total_requests}\n"

        report += f"🛠️ إجمالي الخدمات: {len(services)}"

        

        await update.message.reply_text(report, reply_markup=services_admin_kb())

        return States.MANAGE_SERVICES

    

    elif text == "📄 كشف الخدمات":

        await update.message.reply_text("📄 اختر نوع الكشف:", reply_markup=service_report_kb())

        return States.SERVICE_REPORT

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت للقائمة الرئيسية للأدمن.", reply_markup=admin_menu_kb())

        return States.ADMIN_MENU

    

    return States.MANAGE_SERVICES



async def admin_add_service_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context):

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    service_name = update.message.text.strip()

    if service_name in ("🔙 رجوع", "❌ إلغاء"):

        await update.message.reply_text("⬅️ رجعت لقائمة إدارة الخدمات.", reply_markup=services_admin_kb())

        return States.MANAGE_SERVICES

    

    if add_service_to_db(service_name):

        await update.message.reply_text(

            f"✅ تم إضافة خدمة {service_name} بنجاح.\n"

            f"📄 تم إنشاء ملف CSV منفصل للخدمة.",

            reply_markup=services_admin_kb()

        )

    else:

        await update.message.reply_text(f"⚠️ فشل إضافة الخدمة. قد تكون موجودة مسبقاً.", reply_markup=services_admin_kb())

    

    return States.MANAGE_SERVICES



async def admin_delete_service_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    services = get_services_from_db()

    if not services:

        await update.message.reply_text("⚠️ لا توجد خدمات لحذفها.", reply_markup=services_admin_kb())

        return States.MANAGE_SERVICES

    

    selected = update.message.text.strip()

    if selected == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت لقائمة إدارة الخدمات.", reply_markup=services_admin_kb())

        return States.MANAGE_SERVICES

    

    if delete_service_from_db(selected):

        await update.message.reply_text(

            f"✅ تم حذف خدمة {selected} بنجاح.\n"

            f"🗑️ تم حذف ملف CSV الخاص بالخدمة.",

            reply_markup=services_admin_kb()

        )

    else:

        await update.message.reply_text(f"⚠️ فشل حذف الخدمة. قد تكون غير موجودة.", reply_markup=services_admin_kb())

    

    return States.MANAGE_SERVICES



# معالجة كشوفات الخدمات

async def service_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    

    if text == "📄 كشف لخدمة واحدة":

        services = get_services_from_db()

        if not services:

            await update.message.reply_text("⚠️ لا توجد خدمات مضافة.", reply_markup=service_report_kb())

            return States.SERVICE_REPORT

        

        await update.message.reply_text("📋 اختر الخدمة للحصول على كشفها:", reply_markup=services_selection_kb(services))

        return States.SELECT_SERVICE_FOR_REPORT

    

    elif text == "📄 كشف لكل الخدمات":

        requests = get_service_requests_from_db()

        if not requests:

            await update.message.reply_text("⚠️ لا توجد طلبات خدمات حتى الآن.", reply_markup=service_report_kb())

            return States.SERVICE_REPORT

        

        # إنشاء تقرير شامل

        with open("all_services_report.csv", "w", newline="", encoding="utf-8") as f:

            writer = csv.writer(f)

            writer.writerow(["ID", "رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"])

            for req in requests:

                writer.writerow(req)

        

        await update.message.reply_document(

            document=open("all_services_report.csv", "rb"),

            filename="all_services_report.csv",

            caption="📄 كشف جميع طلبات الخدمات"

        )

        

        # حذف الملف المؤقت

        os.remove("all_services_report.csv")

        return States.SERVICE_REPORT

    

    elif text == "🗑️ حذف كشوف الخدمات":

        await update.message.reply_text("🗑️ اختر نوع الحذف:", reply_markup=service_delete_report_kb())

        return States.DELETE_SERVICE_REPORT

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت لقائمة إدارة الخدمات.", reply_markup=services_admin_kb())

        return States.MANAGE_SERVICES

    

    return States.SERVICE_REPORT



# معالج اختيار خدمة للكشف

async def select_service_for_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    selected_service = update.message.text.strip()

    if selected_service == "🔙 رجوع":

        await update.message.reply_text("📄 اختر نوع الكشف:", reply_markup=service_report_kb())

        return States.SERVICE_REPORT

    

    services = get_services_from_db()

    service_names = [s["service_name"] for s in services]

    

    if selected_service not in service_names:

        await update.message.reply_text("⚠️ الخدمة المختارة غير صحيحة.", reply_markup=services_selection_kb(services))

        return States.SELECT_SERVICE_FOR_REPORT

    

    # إرسال ملف CSV الخاص بالخدمة

    service_csv_file = os.path.join(SERVICES_CSV_DIR, f"{selected_service}.csv")

    

    if not os.path.exists(service_csv_file):

        await update.message.reply_text("⚠️ لا يوجد كشف لهذه الخدمة حتى الآن.", reply_markup=service_report_kb())

        return States.SERVICE_REPORT

    

    # التحقق من وجود بيانات في الملف

    requests_count = count_csv_rows(service_csv_file)

    if requests_count == 0:

        await update.message.reply_text(f"⚠️ لا توجد طلبات لخدمة {selected_service} حتى الآن.", reply_markup=service_report_kb())

        return States.SERVICE_REPORT

    

    await update.message.reply_document(

        document=open(service_csv_file, "rb"),

        filename=f"{selected_service}_report.csv",

        caption=f"📄 كشف طلبات خدمة {selected_service}\n"

                f"📊 إجمالي الطلبات: {requests_count}"

    )

    

    await update.message.reply_text("📄 اختر نوع الكشف:", reply_markup=service_report_kb())

    return States.SERVICE_REPORT



# معالجة حذف كشوف الخدمات

async def delete_service_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    

    if text == "🗑️ حذف كشف خدمة واحدة":

        services = get_services_from_db()

        if not services:

            await update.message.reply_text("⚠️ لا توجد خدمات مضافة.", reply_markup=service_delete_report_kb())

            return States.DELETE_SERVICE_REPORT

        

        await update.message.reply_text("📋 اختر الخدمة لحذف كشفها:", reply_markup=services_selection_kb(services))

        return States.SELECT_SERVICE_FOR_DELETE

    

    elif text == "🗑️ حذف كل الكشوفات":

        await update.message.reply_text(

            "⚠️ هل أنت متأكد من حذف جميع كشوفات الخدمات؟\n\n"

            "هذا الإجراء لا يمكن التراجع عنه.",

            reply_markup=confirm_delete_kb()

        )

        return States.CONFIRM_DELETE_SERVICE_REPORT

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("📄 اختر نوع الكشف:", reply_markup=service_report_kb())

        return States.SERVICE_REPORT

    

    return States.DELETE_SERVICE_REPORT



# معالج اختيار خدمة للحذف

async def select_service_for_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    selected_service = update.message.text.strip()

    if selected_service == "🔙 رجوع":

        await update.message.reply_text("🗑️ اختر نوع الحذف:", reply_markup=service_delete_report_kb())

        return States.DELETE_SERVICE_REPORT

    

    services = get_services_from_db()

    service_names = [s["service_name"] for s in services]

    

    if selected_service not in service_names:

        await update.message.reply_text("⚠️ الخدمة المختارة غير صحيحة.", reply_markup=services_selection_kb(services))

        return States.SELECT_SERVICE_FOR_DELETE

    

    context.user_data["service_to_delete"] = selected_service

    await update.message.reply_text(

        f"⚠️ هل أنت متأكد من حذف كشف خدمة {selected_service}؟\n\n"

        f"هذا الإجراء لا يمكن التراجع عنه.",

        reply_markup=confirm_delete_service_kb()

    )

    return States.CONFIRM_DELETE_SINGLE_SERVICE



# تأكيد حذف خدمة واحدة

async def confirm_delete_single_service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    

    if text == "✅ نعم، احذف كشف الخدمة":

        service_name = context.user_data.get("service_to_delete")

        

        if delete_service_requests_by_service(service_name):

            await update.message.reply_text(

                f"✅ تم حذف كشف خدمة {service_name} بنجاح.",

                reply_markup=service_delete_report_kb()

            )

        else:

            await update.message.reply_text(

                f"⚠️ فشل حذف كشف خدمة {service_name}.",

                reply_markup=service_delete_report_kb()

            )

    else:

        await update.message.reply_text("❌ تم إلغاء حذف كشف الخدمة.", reply_markup=service_delete_report_kb())

    

    context.user_data.pop("service_to_delete", None)

    return States.DELETE_SERVICE_REPORT



# تأكيد حذف جميع كشوف الخدمات

async def confirm_delete_all_services_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    

    if text == "✅ نعم، احذف الكشوفات":

        if delete_all_service_requests():

            await update.message.reply_text(

                "✅ تم حذف جميع كشوفات الخدمات بنجاح.",

                reply_markup=service_delete_report_kb()

            )

        else:

            await update.message.reply_text(

                "⚠️ فشل حذف كشوفات الخدمات.",

                reply_markup=service_delete_report_kb()

            )

    else:

        await update.message.reply_text("❌ تم إلغاء حذف كشوفات الخدمات.", reply_markup=service_delete_report_kb())

    

    return States.DELETE_SERVICE_REPORT



# =========================

# Services: member side

# =========================



async def services_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    services = get_services_from_db()

    if not services:

        await update.message.reply_text("⚠️ لا توجد خدمات مضافة حالياً. يرجى مراجعة الإدارة.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    await update.message.reply_text("📌 اختر الخدمة المطلوبة:", reply_markup=services_menu_kb(services))

    return States.SERVICES_MENU



async def services_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    choice = update.message.text.strip()

    if choice == "🔙 رجوع":

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    services = get_services_from_db()

    service_names = [s["service_name"] for s in services]

    

    if choice not in service_names:

        await update.message.reply_text("⚠️ الخدمة المختارة غير صحيحة. يرجى الاختيار من القائمة.", reply_markup=services_menu_kb(services))

        return States.SERVICES_MENU

    

    context.user_data["selected_service"] = choice

    await update.message.reply_text(

        f"📋 الخدمة المختارة: {choice}\n\n"

        "أدخل رقم جوازك للمتابعة:",

        reply_markup=cancel_or_back_kb()

    )

    return States.SERVICE_PASSPORT



async def service_enter_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):

    passport = update.message.text.strip()

    if passport in ("🔙 رجوع", "❌ إلغاء"):

        context.user_data.pop("selected_service", None)

        await go_main_menu(update, context)

        return ConversationHandler.END

    

    service_name = context.user_data.get("selected_service")

    

    member = get_member_by_passport(passport)

    

    if not member:

        await update.message.reply_text(

            "⚠️ لم يتم العثور على بياناتك في النظام.\n"

            "يجب عليك التسجيل أولاً قبل طلب الخدمة.",

            reply_markup=main_menu_kb()

        )

        context.user_data.clear()

        return ConversationHandler.END

    

    if check_existing_service_request(passport, service_name):

        await update.message.reply_text(

            f"⚠️ لقد طلبت خدمة {service_name} مسبقاً.\n"

            "لا يمكنك طلب نفس الخدمة مرة أخرى.",

            reply_markup=main_menu_kb()

        )

        context.user_data.clear()

        return ConversationHandler.END

    

    requester = member.get("الاسم") if member else "غير مسجل"

    add_service_request(passport, service_name, requester)

    

    await update.message.reply_text(

        f"✅ تم تقديم طلب {service_name} بنجاح.\n"

        "شكراً لاستخدامك منصة الجالية السودانية بأسوان.",

        reply_markup=main_menu_kb()

    )

    

    context.user_data.clear()

    return ConversationHandler.END



# =========================

# الإحصائيات

# =========================



async def admin_stats_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    

    if text == "📋 عرض الملخص":

        members = read_csv_file(MEMBERS_FILE)

        deliveries = read_csv_file(DELIVERIES_FILE)

        users = read_csv_file(USERS_FILE)

        assistants = read_csv_file(ASSISTANTS_FILE)

        service_requests = get_service_requests_from_db()

        

        total_family_members = 0

        for member in members:

            try:

                family_count = int(member.get("عدد_افراد_الاسرة", "1"))

                total_family_members += family_count

            except ValueError:

                total_family_members += 1

        

        report = (

            f"📊 الإحصائيات العامة:\n\n"

            f"👥 إجمالي المسجلين: {len(members)}\n"

            f"👨‍👩‍👧‍👦 إجمالي أفراد الأسر: {total_family_members}\n"

            f"📦 إجمالي التسليمات: {len(deliveries)}\n"

            f"👤 إجمالي المستخدمين: {len(users)}\n"

            f"👮 إجمالي المشرفين: {len(assistants)}\n"

            f"📋 إجمالي طلبات الخدمات: {len(service_requests)}\n"

        )

        

        await update.message.reply_text(report, reply_markup=stats_choice_kb())

        return States.STATS_MENU

    

    elif text == "📥 تنزيل تقرير CSV":

        members = read_csv_file(MEMBERS_FILE)

        total_family_members = 0

        for member in members:

            try:

                family_count = int(member.get("عدد_افراد_الاسرة", "1"))

                total_family_members += family_count

            except ValueError:

                total_family_members += 1

                

        with open(STATISTICS_FILE, "w", newline="", encoding="utf-8") as f:

            writer = csv.writer(f)

            writer.writerow(["نوع الإحصائية", "العدد"])

            writer.writerow(["إجمالي المسجلين", len(members)])

            writer.writerow(["إجمالي أفراد الأسر", total_family_members])

            writer.writerow(["إجمالي التسليمات", len(read_csv_file(DELIVERIES_FILE))])

            writer.writerow(["إجمالي المستخدمين", len(read_csv_file(USERS_FILE))])

            writer.writerow(["إجمالي المشرفين", len(read_csv_file(ASSISTANTS_FILE))])

            writer.writerow(["إجمالي طلبات الخدمات", len(get_service_requests_from_db())])

        

        await update.message.reply_document(

            document=open(STATISTICS_FILE, "rb"),

            filename="statistics_report.csv",

            caption="📊 تقرير الإحصائيات"

        )

        return States.STATS_MENU

    

    elif text == "🗑️ حذف الملخص":

        await update.message.reply_text(

            "⚠️ هل أنت متأكد من أنك تريد حذف جميع الإحصائيات؟\n\n"

            "هذا الإجراء لا يمكن التراجع عنه.",

            reply_markup=confirm_delete_stats_kb(),

        )

        return States.CONFIRM_DELETE_STATS

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت للقائمة الرئيسية للأدمن.", reply_markup=admin_menu_kb())

        return States.ADMIN_MENU

    

    return States.STATS_MENU



async def admin_delete_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.text == "✅ نعم، احذف الملخص":

        if os.path.exists(DELIVERIES_FILE):

            os.remove(DELIVERIES_FILE)

        ensure_csv(DELIVERIES_FILE, ["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"])

        

        delete_all_service_requests()

        

        await update.message.reply_text("✅ تم حذف جميع الإحصائيات.", reply_markup=stats_choice_kb())

    else:

        await update.message.reply_text("❌ تم إلغاء حذف الإحصائيات.", reply_markup=stats_choice_kb())

    return States.STATS_MENU



# =========================

# إدارة بيانات الأعضاء

# =========================



async def manage_members_data_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":

        await update.message.reply_text("⚠️ ليس لديك صلاحيات الوصول.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    

    if text == "⬇️ تنزيل البيانات":

        if not os.path.exists(MEMBERS_FILE) or os.stat(MEMBERS_FILE).st_size == 0:

            await update.message.reply_text("⚠️ لا توجد بيانات مسجلين حتى الآن.", reply_markup=manage_members_data_kb())

            return States.MANAGE_MEMBERS_DATA

        

        await update.message.reply_document(

            document=open(MEMBERS_FILE, "rb"),

            filename="members.csv",

            caption="📥 بيانات المسجلين"

        )

        return States.MANAGE_MEMBERS_DATA

    

    elif text == "🗑️ مسح البيانات":

        await update.message.reply_text(

            "⚠️ هل أنت متأكد من أنك تريد حذف جميع بيانات المسجلين؟\n\n"

            "هذا الإجراء لا يمكن التراجع عنه.",

            reply_markup=confirm_delete_members_kb(),

        )

        return States.CONFIRM_DELETE_MEMBERS

    

    elif text == "📊 ملخص المسجلين":

        members = read_csv_file(MEMBERS_FILE)

        if not members:

            await update.message.reply_text("⚠️ لا توجد بيانات مسجلين حتى الآن.", reply_markup=manage_members_data_kb())

            return States.MANAGE_MEMBERS_DATA

        

        total = len(members)

        total_family_members = 0

        roles = {}

        

        for member in members:

            role = member.get("الصفة", "غير محدد")

            roles[role] = roles.get(role, 0) + 1

            

            try:

                family_count = int(member.get("عدد_افراد_الاسرة", "1"))

                total_family_members += family_count

            except ValueError:

                total_family_members += 1

        

        report = f"📊 ملخص المسجلين:\n\n"

        report += f"إجمالي المسجلين: {total}\n"

        report += f"إجمالي أفراد الأسر: {total_family_members}\n\n"

        report += f"التوزيع حسب الصفة:\n"

        for role, count in roles.items():

            report += f"- {role}: {count}\n"

        

        await update.message.reply_text(report, reply_markup=manage_members_data_kb())

        return States.MANAGE_MEMBERS_DATA

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت لقائمة إدارة الحسابات.", reply_markup=account_management_kb())

        return States.ACCOUNT_MANAGEMENT

    

    return States.MANAGE_MEMBERS_DATA



async def admin_clear_members(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.text == "✅ نعم، احذف بيانات المسجلين":

        if os.path.exists(MEMBERS_FILE):

            os.remove(MEMBERS_FILE)

        ensure_csv(MEMBERS_FILE, ["الاسم", "الجواز", "الهاتف", "العنوان", "الصفة", "عدد_افراد_الاسرة"])

        await update.message.reply_text("🗑️ تم مسح جميع بيانات المسجلين.", reply_markup=manage_members_data_kb())

    else:

        await update.message.reply_text("❌ تم إلغاء حذف البيانات.", reply_markup=manage_members_data_kb())

    return States.MANAGE_MEMBERS_DATA



# =========================

# إدارة المشرفين

# =========================



async def manage_assistants_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    

    if text == "➕ إضافة مشرف":

        await update.message.reply_text("👤 أدخل اسم المستخدم للمشرف الجديد:", reply_markup=cancel_or_back_kb())

        return States.CREATE_ASSISTANT_USER

    

    elif text == "🗑️ حذف مشرف":

        assistants = read_csv_file(ASSISTANTS_FILE)

        if not assistants:

            await update.message.reply_text("⚠️ لا يوجد مشرفين مسجلين.", reply_markup=assistants_management_kb())

            return States.MANAGE_ASSISTANTS

        

        keyboard = [[KeyboardButton(a["username"])] for a in assistants]

        keyboard.append([KeyboardButton("🔙 رجوع")])

        await update.message.reply_text(

            "👥 اختر المشرف للحذف:",

            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        )

        return States.DELETE_ASSISTANT

    

    elif text == "🔑 تغيير كلمة المرور":

        assistants = read_csv_file(ASSISTANTS_FILE)

        if not assistants:

            await update.message.reply_text("⚠️ لا يوجد مشرفين مسجلين.", reply_markup=assistants_management_kb())

            return States.MANAGE_ASSISTANTS

        

        keyboard = [[KeyboardButton(a["username"])] for a in assistants]

        keyboard.append([KeyboardButton("🔙 رجوع")])

        await update.message.reply_text(

            "👥 اختر المشرف لتغيير كلمة المرور:",

            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        )

        return States.CHANGE_ASSISTANT_USER

    

    elif text == "📋 كشف المشرفين":

        assistants = read_csv_file(ASSISTANTS_FILE)

        if not assistants:

            await update.message.reply_text("⚠️ لا يوجد مشرفين مسجلين.", reply_markup=assistants_management_kb())

            return States.MANAGE_ASSISTANTS

        

        report = "👥 قائمة المشرفين:\n\n"

        for i, assistant in enumerate(assistants, 1):

            report += f"{i}. {assistant['username']}\n"

        

        await update.message.reply_text(report, reply_markup=assistants_management_kb())

        return States.MANAGE_ASSISTANTS

    

    elif text == "📥 تنزيل قائمة المشرفين":

        if not os.path.exists(ASSISTANTS_FILE) or os.stat(ASSISTANTS_FILE).st_size == 0:

            await update.message.reply_text("⚠️ لا يوجد مشرفين مسجلين.", reply_markup=assistants_management_kb())

            return States.MANAGE_ASSISTANTS

        

        await update.message.reply_document(

            document=open(ASSISTANTS_FILE, "rb"),

            filename="assistants.csv",

            caption="📥 قائمة المشرفين"

        )

        return States.MANAGE_ASSISTANTS

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت لقائمة إدارة الحسابات.", reply_markup=account_management_kb())

        return States.ACCOUNT_MANAGEMENT

    

    return States.MANAGE_ASSISTANTS



async def create_assistant_user(update: Update, context: ContextTypes.DEFAULT_TYPE):

    new_user = update.message.text.strip()

    if new_user in ("🔙 رجوع", "❌ إلغاء"):

        await update.message.reply_text("تم الإلغاء.", reply_markup=assistants_management_kb())

        return States.MANAGE_ASSISTANTS

    

    assistants = read_csv_file(ASSISTANTS_FILE)

    if any(a.get("username") == new_user for a in assistants):

        await update.message.reply_text("⚠️ اسم المستخدم موجود مسبقاً. اختر اسمًا آخر:", reply_markup=cancel_or_back_kb())

        return States.CREATE_ASSISTANT_USER

    

    context.user_data["new_assistant_user"] = new_user

    await update.message.reply_text("🔐 أدخل كلمة المرور للمشرف الجديد:", reply_markup=cancel_or_back_kb())

    return States.CREATE_ASSISTANT_PASS



async def create_assistant_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):

    new_pass = update.message.text.strip()

    if new_pass == "🔙 رجوع":

        await update.message.reply_text("👤 أدخل اسم المستخدم للمشرف الجديد:", reply_markup=cancel_or_back_kb())

        return States.CREATE_ASSISTANT_USER

    if new_pass == "❌ إلغاء":

        await update.message.reply_text("تم الإلغاء.", reply_markup=assistants_management_kb())

        return States.MANAGE_ASSISTANTS

    

    new_user = context.user_data.get("new_assistant_user")

    append_csv_row(ASSISTANTS_FILE, {"username": new_user, "password": new_pass}, ["username", "password"])

    

    await update.message.reply_text(

        f"✅ تم إضافة المشرف {new_user} بنجاح.",

        reply_markup=assistants_management_kb()

    )

    return States.MANAGE_ASSISTANTS



async def delete_assistant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    assistant_to_delete = update.message.text.strip()

    if assistant_to_delete == "🔙 رجوع":

        await update.message.reply_text("تم الإلغاء.", reply_markup=assistants_management_kb())

        return States.MANAGE_ASSISTANTS

    

    assistants = read_csv_file(ASSISTANTS_FILE)

    updated_assistants = [a for a in assistants if a.get("username") != assistant_to_delete]

    write_csv_file(ASSISTANTS_FILE, updated_assistants, ["username", "password"])

    

    await update.message.reply_text(

        f"✅ تم حذف المشرف {assistant_to_delete} بنجاح.",

        reply_markup=assistants_management_kb()

    )

    return States.MANAGE_ASSISTANTS



async def get_new_password_for_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):

    selected_user = update.message.text.strip()

    if selected_user == "🔙 رجوع":

        await update.message.reply_text("تم الإلغاء.", reply_markup=assistants_management_kb())

        return States.MANAGE_ASSISTANTS

    

    context.user_data["change_pass_user"] = selected_user

    await update.message.reply_text("🔐 أدخل كلمة المرور الجديدة:", reply_markup=cancel_or_back_kb())

    return States.CHANGE_ASSISTANT_PASS



async def update_assistant_password(update: Update, context: ContextTypes.DEFAULT_TYPE):

    new_password = update.message.text.strip()

    if new_password == "🔙 رجوع":

        return await get_new_password_for_assistant(update, context)

    if new_password == "❌ إلغاء":

        await update.message.reply_text("تم الإلغاء.", reply_markup=assistants_management_kb())

        return States.MANAGE_ASSISTANTS

    

    user_to_change = context.user_data.get("change_pass_user")

    assistants = read_csv_file(ASSISTANTS_FILE)

    

    for assistant in assistants:

        if assistant.get("username") == user_to_change:

            assistant["password"] = new_password

    

    write_csv_file(ASSISTANTS_FILE, assistants, ["username", "password"])

    

    await update.message.reply_text(

        f"✅ تم تغيير كلمة المرور للمشرف {user_to_change} بنجاح.",

        reply_markup=assistants_management_kb()

    )

    return States.MANAGE_ASSISTANTS



# =========================

# كشوفات التسليم

# =========================



async def manage_delivery_reports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    

    if text == "⬇️ تنزيل الكشوفات":

        if not os.path.exists(DELIVERIES_FILE) or os.stat(DELIVERIES_FILE).st_size == 0:

            await update.message.reply_text("⚠️ لا توجد كشوفات تسليم حتى الآن.", reply_markup=delivery_reports_kb())

            return States.MANAGE_DELIVERY_REPORTS

        

        await update.message.reply_document(

            document=open(DELIVERIES_FILE, "rb"),

            filename="deliveries.csv",

            caption="📥 كشوفات التسليم"

        )

        return States.MANAGE_DELIVERY_REPORTS

    

    elif text == "🗑️ حذف الكشوفات":

        await update.message.reply_text(

            "⚠️ هل أنت متأكد من أنك تريد حذف جميع كشوفات التسليم؟\n\n"

            "هذا الإجراء لا يمكن التراجع عنه.",

            reply_markup=confirm_delete_kb(),

        )

        return States.CONFIRM_DELETE_DELIVERIES

    

    elif text == "📊 عرض الملخص":

        deliveries = read_csv_file(DELIVERIES_FILE)

        if not deliveries:

            await update.message.reply_text("⚠️ لا توجد كشوفات تسليم حتى الآن.", reply_markup=delivery_reports_kb())

            return States.MANAGE_DELIVERY_REPORTS

        

        total = len(deliveries)

        assistants = {}

        for delivery in deliveries:

            assistant = delivery.get("المشرف", "غير معروف")

            assistants[assistant] = assistants.get(assistant, 0) + 1

        

        report = f"📊 ملخص التسليمات:\n\nإجمالي التسليمات: {total}\n\nالتوزيع حسب المشرف:\n"

        for assistant, count in assistants.items():

            report += f"- {assistant}: {count}\n"

        

        await update.message.reply_text(report, reply_markup=delivery_reports_kb())

        return States.MANAGE_DELIVERY_REPORTS

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت للقائمة الرئيسية للأدمن.", reply_markup=admin_menu_kb())

        return States.ADMIN_MENU

    

    return States.MANAGE_DELIVERY_REPORTS



async def delete_delivery_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.text == "✅ نعم، احذف الكشوفات":

        if os.path.exists(DELIVERIES_FILE):

            os.remove(DELIVERIES_FILE)

        ensure_csv(DELIVERIES_FILE, ["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"])

        await update.message.reply_text("✅ تم حذف جميع كشوفات التسليم.", reply_markup=delivery_reports_kb())

    else:

        await update.message.reply_text("❌ تم إلغاء حذف الكشوفات.", reply_markup=delivery_reports_kb())

    return States.MANAGE_DELIVERY_REPORTS



# =========================

# تسجيل التسليم للمشرفين

# =========================



async def record_delivery_process(update: Update, context: ContextTypes.DEFAULT_TYPE):

    passport = update.message.text.strip()

    if passport in ("🔙 رجوع", "❌ إلغاء"):

        await update.message.reply_text("تم الإلغاء.", reply_markup=assistant_menu_kb())

        return States.ASSISTANT_MENU

    

    members = read_csv_file(MEMBERS_FILE)

    member = next((m for m in members if m.get("الجواز") == passport), None)

    

    if not member:

        await update.message.reply_text("⚠️ لم يتم العثور على العضو. تأكد من رقم الجواز.", reply_markup=cancel_or_back_kb())

        return States.RECORD_DELIVERY_PASSPORT

    

    existing_delivery = check_existing_delivery(passport)

    if existing_delivery:

        warning_message = (

            f"⚠️ تحذير: العضو {member.get('الاسم')} تم تسليمه من قبل!\n\n"

            f"المشرف: {existing_delivery.get('المشرف')}\n"

            f"التاريخ: {existing_delivery.get('تاريخ_التسليم')}\n\n"

            f"هل تريد تسليمه مرة أخرى؟"

        )

        context.user_data["pending_delivery_passport"] = passport

        context.user_data["pending_delivery_name"] = member.get("الاسم")

        

        await update.message.reply_text(warning_message, reply_markup=confirm_delivery_kb())

        return States.CONFIRM_DELIVERY

    

    context.user_data["pending_delivery_passport"] = passport

    context.user_data["pending_delivery_name"] = member.get("الاسم")

    

    await update.message.reply_text(

        f"✅ تم العثور على العضو: {member.get('الاسم')}\n"

        f"📞 الهاتف: {member.get('الهاتف')}\n\n"

        f"هل تريد تأكيد التسليم؟",

        reply_markup=confirm_delivery_kb()

    )

    return States.CONFIRM_DELIVERY



async def record_delivery_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if text == "✅ نعم - تأكيد":

        passport = context.user_data.get("pending_delivery_passport")

        name = context.user_data.get("pending_delivery_name")

        assistant_user = context.user_data.get("login_user")

        

        append_csv_row(

            DELIVERIES_FILE,

            {

                "المشرف": assistant_user,

                "رقم_الجواز": passport,

                "اسم_العضو": name,

                "تاريخ_التسليم": datetime.now().strftime("%Y-%m-%d %H:%M")

            },

            ["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"]

        )

        

        await update.message.reply_text(

            "✅ تم تسجيل التسليم بنجاح.",

            reply_markup=assistant_menu_kb()

        )

        return States.ASSISTANT_MENU

    else:

        await update.message.reply_text("❌ تم إلغاء التسجيل.", reply_markup=assistant_menu_kb())

        return States.ASSISTANT_MENU



async def assistant_view_deliveries_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not validate_admin_session(context):

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END

    

    text = update.message.text

    assistant_user = context.user_data.get("login_user")

    deliveries = read_csv_file(DELIVERIES_FILE)

    assistant_deliveries = [d for d in deliveries if d.get("المشرف") == assistant_user]

    

    if text == "📥 تحميل":

        if not assistant_deliveries:

            await update.message.reply_text("⚠️ لا توجد تسليمات مسجلة حتى الآن.", reply_markup=assistant_delivery_reports_kb())

            return States.ASSISTANT_VIEW_DELIVERIES

        

        temp_filename = f"{assistant_user}_deliveries.csv"

        with open(temp_filename, "w", newline="", encoding="utf-8") as f:

            writer = csv.DictWriter(f, fieldnames=["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"])

            writer.writeheader()

            writer.writerows(assistant_deliveries)

        

        await update.message.reply_document(

            document=open(temp_filename, "rb"),

            filename=temp_filename,

            caption="📥 كشوفات التسليم"

        )

        

        os.remove(temp_filename)

        return States.ASSISTANT_VIEW_DELIVERIES

    

    elif text == "📊 ملخص":

        if not assistant_deliveries:

            await update.message.reply_text("⚠️ لا توجد تسليمات مسجلة حتى الآن.", reply_markup=assistant_delivery_reports_kb())

            return States.ASSISTANT_VIEW_DELIVERIES

        

        total = len(assistant_deliveries)

        dates = {}

        for delivery in assistant_deliveries:

            date_str = delivery.get("تاريخ_التسليم", "").split(" ")[0]

            dates[date_str] = dates.get(date_str, 0) + 1

        

        report = f"📊 ملخص تسليماتك:\n\nإجمالي التسليمات: {total}\n\nالتوزيع حسب التاريخ:\n"

        for date_str, count in dates.items():

            report += f"- {date_str}: {count}\n"

        

        await update.message.reply_text(report, reply_markup=assistant_delivery_reports_kb())

        return States.ASSISTANT_VIEW_DELIVERIES

    

    elif text == "🔙 رجوع":

        await update.message.reply_text("⬅️ رجعت لقائمة المشرف.", reply_markup=assistant_menu_kb())

        return States.ASSISTANT_MENU

    

    return States.ASSISTANT_VIEW_DELIVERIES



# =========================

# وظائف مساعدة إضافية

# =========================



async def back_to_admin_only(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("user_type") == "main_admin":

        await update.message.reply_text("⬅️ رجعت لقائمة الأدمن.", reply_markup=admin_menu_kb())

        return States.ADMIN_MENU

    elif context.user_data.get("user_type") == "assistant":

        await update.message.reply_text("⬅️ رجعت لقائمة المشرف.", reply_markup=assistant_menu_kb())

        return States.ASSISTANT_MENU

    else:

        await update.message.reply_text("⚠️ ليس لديك صلاحيات.", reply_markup=main_menu_kb())

        return ConversationHandler.END



# =========================

# Main function

# =========================



def main():

    # تهيئة قاعدة البيانات

    init_services_db()

    

    # إنشاء التطبيق

    persistence = PicklePersistence(filepath="conversationbot")

    application = Application.builder().token(TOKEN).persistence(persistence).build()

    

    # تسجيل handlers المحادثة

    conv_handler = ConversationHandler(

        entry_points=[MessageHandler(filters.Text(["📝 التسجيل"]), register_start)],

        states={

            States.ASK_NAME: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), ask_passport)],

            States.ASK_PASSPORT: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), ask_phone)],

            States.ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), ask_address)],

            States.ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), ask_role)],

            States.ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), ask_family_members)],

            States.ASK_FAMILY_MEMBERS: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), confirm_registration)],

        },

        fallbacks=[

            MessageHandler(filters.Text(["❌ إلغاء"]), cancel_registration),

            MessageHandler(filters.Text(["🔙 رجوع"]), go_main_menu)

        ],

        name="registration",

        persistent=True,

    )

    

    # handler للخدمات

    services_handler = ConversationHandler(

        entry_points=[MessageHandler(filters.Text(["📌 الخدمات"]), services_menu_start)],

        states={

            States.SERVICES_MENU: [MessageHandler(filters.TEXT & ~filters.Text(["🔙 رجوع"]), services_menu_handler)],

            States.SERVICE_PASSPORT: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), service_enter_passport)],

        },

        fallbacks=[

            MessageHandler(filters.Text(["❌ إلغاء"]), go_main_menu),

            MessageHandler(filters.Text(["🔙 رجوع"]), go_main_menu)

        ],

        name="services",

        persistent=True,

    )

    

    # handler لتسجيل الدخول كأدمن

    admin_login_handler = ConversationHandler(

        entry_points=[MessageHandler(filters.Text(["🔑 دخول"]), admin_login)],

        states={

            States.ADMIN_USER_INPUT: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), admin_get_user)],

            States.ADMIN_PASS_INPUT: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), admin_get_pass)],

            States.ADMIN_MENU: [MessageHandler(filters.TEXT, admin_menu_handler)],

            States.ACCOUNT_MANAGEMENT: [MessageHandler(filters.TEXT, account_management_handler)],

            States.MANAGE_ASSISTANTS: [MessageHandler(filters.TEXT, manage_assistants_menu)],

            States.CREATE_ASSISTANT_USER: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), create_assistant_user)],

            States.CREATE_ASSISTANT_PASS: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), create_assistant_pass)],

            States.DELETE_ASSISTANT: [MessageHandler(filters.TEXT & ~filters.Text(["🔙 رجوع"]), delete_assistant_menu)],

            States.CHANGE_ASSISTANT_USER: [MessageHandler(filters.TEXT & ~filters.Text(["🔙 رجوع"]), get_new_password_for_assistant)],

            States.CHANGE_ASSISTANT_PASS: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), update_assistant_password)],

            States.MANAGE_MEMBERS_DATA: [MessageHandler(filters.TEXT, manage_members_data_menu)],

            States.CONFIRM_DELETE_MEMBERS: [MessageHandler(filters.TEXT, admin_clear_members)],

            States.MANAGE_DELIVERY_REPORTS: [MessageHandler(filters.TEXT, manage_delivery_reports_menu)],

            States.CONFIRM_DELETE_DELIVERIES: [MessageHandler(filters.TEXT, delete_delivery_reports)],

            States.STATS_MENU: [MessageHandler(filters.TEXT, admin_stats_choice_handler)],

            States.CONFIRM_DELETE_STATS: [MessageHandler(filters.TEXT, admin_delete_stats)],

            States.MANAGE_SERVICES: [MessageHandler(filters.TEXT, manage_services_menu)],

            States.ADD_SERVICE: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), admin_add_service_start)],

            States.DELETE_SERVICE: [MessageHandler(filters.TEXT & ~filters.Text(["🔙 رجوع"]), admin_delete_service_start)],

            States.SERVICE_REPORT: [MessageHandler(filters.TEXT, service_report_handler)],

            States.SELECT_SERVICE_FOR_REPORT: [MessageHandler(filters.TEXT, select_service_for_report_handler)],

            States.DELETE_SERVICE_REPORT: [MessageHandler(filters.TEXT, delete_service_report_handler)],

            States.SELECT_SERVICE_FOR_DELETE: [MessageHandler(filters.TEXT, select_service_for_delete_handler)],

            States.CONFIRM_DELETE_SINGLE_SERVICE: [MessageHandler(filters.TEXT, confirm_delete_single_service_handler)],

            States.CONFIRM_DELETE_SERVICE_REPORT: [MessageHandler(filters.TEXT, confirm_delete_all_services_handler)],

            States.BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), admin_broadcast)],

            States.ASSISTANT_MENU: [MessageHandler(filters.TEXT, admin_menu_handler)],

            States.RECORD_DELIVERY_PASSPORT: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), record_delivery_process)],

            States.CONFIRM_DELIVERY: [MessageHandler(filters.TEXT, record_delivery_confirm)],

            States.ASSISTANT_VIEW_DELIVERIES: [MessageHandler(filters.TEXT, assistant_view_deliveries_handler)],

        },

        fallbacks=[

            MessageHandler(filters.Text(["❌ إلغاء"]), go_main_menu),

            MessageHandler(filters.Text(["🔙 رجوع"]), back_to_admin_only)

        ],

        name="admin",

        persistent=True,

    )

    

    # إضافة handlers

    application.add_handler(conv_handler)

    application.add_handler(services_handler)

    application.add_handler(admin_login_handler)

    

    # إضافة handlers للأوامر الأساسية

    application.add_handler(MessageHandler(filters.Text(["❌ إلغاء"]), go_main_menu))

    application.add_handler(MessageHandler(filters.Text(["🔙 رجوع"]), go_main_menu))

    application.add_handler(CommandHandler("start", start))

    application.add_handler(MessageHandler(filters.Text(["ℹ️ عن المنصة"]), about))

    application.add_handler(MessageHandler(filters.Text(["📞 تواصل معنا"]), contact_menu))

    application.add_handler(MessageHandler(filters.Text(["📞 الهاتف"]), contact_phone))

    application.add_handler(MessageHandler(filters.Text(["✉️ البريد الإلكتروني"]), contact_email))

    application.add_handler(MessageHandler(filters.Text(["📱 واتساب"]), contact_whatsapp))

    application.add_handler(MessageHandler(filters.Text(["📘 فيسبوك"]), contact_facebook))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, show_admin_login))

    

    # بدء البوت

    application.run_polling()

# =========================
# Simple main function for Render
# =========================

def main():
    """الدالة الرئيسية المبسطة للتشغيل على Render"""
    try:
        print("🚀 بدء تشغيل بوت الجالية السودانية...")
        
        # التحقق من التوكن
        if not TOKEN or TOKEN == "8342715370:AAGgUMEKd1E0u3hi_u28jMNrZA9RD0v0WXo":
            print("❌ خطأ: يجب تعيين BOT_TOKEN في متغيرات البيئة")
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
        application.add_handler(MessageHandler(filters.Text(["ℹ️ عن المنصة"]), about))
        application.add_handler(MessageHandler(filters.Text(["📞 تواصل معنا"]), contact_menu))
        
        print("✅ تم تحميل جميع الـ handlers")
        print("🤖 البوت جاهز للعمل...")
        
        # بدء البوت
        application.run_polling()
        
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
