# -*- coding: utf-8 -*-

import os
import csv
import sqlite3
import logging
from datetime import datetime, date
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple
import re
import tempfile

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

TOKEN = "8342715370:AAGgUMEKd1E0u3hi_u28jMNrZA9RD0v0WXo"
ADMIN_USER = "Osman"
ADMIN_PASS = "2580"

# قاعدة البيانات الرئيسية
DATABASE = "community_bot.db"

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
    UPLOAD_CSV_FILE = auto()
    CONFIRM_CSV_UPLOAD = auto()
    
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
# Database Helper functions
# =========================

def get_db_connection():
    """إنشاء اتصال مع قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # للحصول على النتائج كـ dictionary
    return conn

def init_database():
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول الأعضاء المسجلين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            passport TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            role TEXT NOT NULL,
            family_members INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # جدول المشرفين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assistants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # جدول التسليمات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assistant TEXT NOT NULL,
            passport TEXT NOT NULL,
            member_name TEXT NOT NULL,
            delivery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # جدول الخدمات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # جدول طلبات الخدمات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passport TEXT NOT NULL,
            service_name TEXT NOT NULL,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            requester TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

# =========================
# Members Database Operations
# =========================

def add_member(name: str, passport: str, phone: str, address: str, role: str, family_members: int) -> bool:
    """إضافة عضو جديد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO members (name, passport, phone, address, role, family_members)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, passport, phone, address, role, family_members))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.exception(f"Error adding member: {e}")
        return False

def add_members_bulk(members_data: List[Dict]) -> Tuple[int, int, List[str]]:
    """إضافة مجموعة من الأعضاء دفعة واحدة
    Returns: (success_count, failed_count, error_messages)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    success_count = 0
    failed_count = 0
    error_messages = []
    
    for member in members_data:
        try:
            cursor.execute("""
                INSERT INTO members (name, passport, phone, address, role, family_members)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                member['name'], 
                member['passport'], 
                member['phone'], 
                member['address'], 
                member['role'], 
                member['family_members']
            ))
            success_count += 1
        except sqlite3.IntegrityError:
            failed_count += 1
            error_messages.append(f"الجواز {member['passport']} موجود مسبقاً")
        except Exception as e:
            failed_count += 1
            error_messages.append(f"خطأ في إضافة {member.get('name', 'مجهول')}: {str(e)}")
    
    conn.commit()
    conn.close()
    return success_count, failed_count, error_messages

def is_passport_registered(passport: str) -> bool:
    """التحقق من تسجيل الجواز"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM members WHERE passport = ?", (passport,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_member_by_passport(passport: str) -> Optional[Dict[str, str]]:
    """الحصول على بيانات العضو بواسطة رقم الجواز"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE passport = ?", (passport,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "الاسم": row["name"],
            "الجواز": row["passport"],
            "الهاتف": row["phone"],
            "العنوان": row["address"],
            "الصفة": row["role"],
            "عدد_افراد_الاسرة": str(row["family_members"])
        }
    return None

def get_all_members() -> List[Dict[str, str]]:
    """الحصول على جميع الأعضاء"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "الاسم": row["name"],
        "الجواز": row["passport"],
        "الهاتف": row["phone"],
        "العنوان": row["address"],
        "الصفة": row["role"],
        "عدد_افراد_الاسرة": str(row["family_members"])
    } for row in rows]

def delete_all_members() -> bool:
    """حذف جميع الأعضاء"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM members")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.exception(f"Error deleting members: {e}")
        return False

def get_members_count() -> int:
    """عدد الأعضاء المسجلين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM members")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_total_family_members() -> int:
    """إجمالي أفراد الأسر"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(family_members) FROM members")
    total = cursor.fetchone()[0]
    conn.close()
    return total or 0

def get_members_by_role() -> Dict[str, int]:
    """توزيع الأعضاء حسب الصفة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, COUNT(*) FROM members GROUP BY role")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

# =========================
# CSV Processing functions
# =========================

def validate_csv_data(csv_data: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """التحقق من صحة بيانات CSV
    Returns: (valid_data, error_messages)
    """
    valid_data = []
    error_messages = []
    required_fields = ['name', 'passport', 'phone', 'address', 'role', 'family_members']
    
    for i, row in enumerate(csv_data, start=1):
        # التحقق من وجود الحقول المطلوبة
        missing_fields = [field for field in required_fields if not row.get(field, '').strip()]
        if missing_fields:
            error_messages.append(f"الصف {i}: حقول مفقودة - {', '.join(missing_fields)}")
            continue
        
        # التحقق من صحة عدد أفراد الأسرة
        try:
            family_count = int(str(row['family_members']).strip())
            if family_count < 1:
                error_messages.append(f"الصف {i}: عدد أفراد الأسرة يجب أن يكون أكبر من صفر")
                continue
        except ValueError:
            error_messages.append(f"الصف {i}: عدد أفراد الأسرة يجب أن يكون رقماً صحيحاً")
            continue
        
        # تنظيف البيانات وإضافتها
        cleaned_row = {
            'name': str(row['name']).strip(),
            'passport': str(row['passport']).strip(),
            'phone': str(row['phone']).strip(),
            'address': str(row['address']).strip(),
            'role': str(row['role']).strip(),
            'family_members': family_count
        }
        
        valid_data.append(cleaned_row)
    
    return valid_data, error_messages

def process_csv_file(file_path: str) -> Tuple[List[Dict], List[str]]:
    """معالجة ملف CSV
    Returns: (valid_data, error_messages)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # محاولة تحديد الفاصل
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            # البحث عن الفاصل المناسب
            delimiter = ','
            if sample.count(';') > sample.count(','):
                delimiter = ';'
            elif sample.count('\t') > sample.count(','):
                delimiter = '\t'
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # تحويل أسماء الأعمدة للإنجليزية إذا كانت بالعربية
            fieldname_mapping = {
                'الاسم': 'name',
                'الجواز': 'passport', 
                'رقم_الجواز': 'passport',
                'الهاتف': 'phone',
                'رقم_الهاتف': 'phone',
                'العنوان': 'address',
                'الصفة': 'role',
                'عدد_افراد_الاسرة': 'family_members',
                'عدد_الأفراد': 'family_members',
                'أفراد_الاسرة': 'family_members'
            }
            
            csv_data = []
            for row in reader:
                # تحويل أسماء الحقول
                converted_row = {}
                for key, value in row.items():
                    if key in fieldname_mapping:
                        converted_row[fieldname_mapping[key]] = value
                    else:
                        converted_row[key] = value
                csv_data.append(converted_row)
            
            return validate_csv_data(csv_data)
            
    except UnicodeDecodeError:
        # محاولة قراءة بترميز مختلف
        try:
            with open(file_path, 'r', encoding='cp1256') as csvfile:
                reader = csv.DictReader(csvfile)
                csv_data = list(reader)
                return validate_csv_data(csv_data)
        except Exception as e:
            return [], [f"خطأ في قراءة الملف: {str(e)}"]
    except Exception as e:
        return [], [f"خطأ في معالجة الملف: {str(e)}"]

def create_csv_template() -> str:
    """إنشاء ملف نموذج CSV"""
    template_data = [
        {
            'name': 'محمد أحمد علي',
            'passport': 'A1234567',
            'phone': '01234567890',
            'address': 'شارع النيل، أسوان',
            'role': 'رب أسرة',
            'family_members': '4'
        },
        {
            'name': 'فاطمة محمد إبراهيم',
            'passport': 'B7654321',
            'phone': '01987654321',
            'address': 'حي السوق، أسوان',
            'role': 'ربة منزل',
            'family_members': '3'
        }
    ]
    
    template_filename = 'template_members.csv'
    with open(template_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'passport', 'phone', 'address', 'role', 'family_members']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # كتابة العناوين بالعربية
        arabic_headers = {
            'name': 'الاسم',
            'passport': 'الجواز', 
            'phone': 'الهاتف',
            'address': 'العنوان',
            'role': 'الصفة',
            'family_members': 'عدد_افراد_الاسرة'
        }
        writer.writerow(arabic_headers)
        writer.writerows(template_data)
    
    return template_filename

# =========================
# Users Database Operations
# =========================

def add_user_if_not_exists(user_id: int, username: str):
    """إضافة مستخدم جديد إذا لم يكن موجوداً"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        """, (str(user_id), username or ""))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.exception(f"Error adding user: {e}")

def get_all_users() -> List[Dict[str, str]]:
    """الحصول على جميع المستخدمين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY user_id")
    rows = cursor.fetchall()
    conn.close()
    return [{"user_id": row["user_id"], "username": row["username"]} for row in rows]

def get_users_count() -> int:
    """عدد المستخدمين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# =========================
# Assistants Database Operations
# =========================

def add_assistant(username: str, password: str) -> bool:
    """إضافة مشرف جديد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO assistants (username, password)
            VALUES (?, ?)
        """, (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.exception(f"Error adding assistant: {e}")
        return False

def delete_assistant(username: str) -> bool:
    """حذف مشرف"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM assistants WHERE username = ?", (username,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted > 0
    except Exception as e:
        logger.exception(f"Error deleting assistant: {e}")
        return False

def update_assistant_password(username: str, new_password: str) -> bool:
    """تحديث كلمة مرور مشرف"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE assistants SET password = ? WHERE username = ?
        """, (new_password, username))
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        return updated > 0
    except Exception as e:
        logger.exception(f"Error updating assistant password: {e}")
        return False

def get_all_assistants() -> List[Dict[str, str]]:
    """الحصول على جميع المشرفين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM assistants ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{"username": row["username"], "password": row["password"]} for row in rows]

def validate_assistant(username: str, password: str) -> bool:
    """التحقق من صحة بيانات المشرف"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM assistants WHERE username = ? AND password = ?
    """, (username, password))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_assistants_count() -> int:
    """عدد المشرفين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM assistants")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# =========================
# Deliveries Database Operations
# =========================

def add_delivery(assistant: str, passport: str, member_name: str) -> bool:
    """إضافة تسليم جديد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deliveries (assistant, passport, member_name)
            VALUES (?, ?, ?)
        """, (assistant, passport, member_name))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.exception(f"Error adding delivery: {e}")
        return False

def check_existing_delivery(passport: str) -> Optional[Dict[str, str]]:
    """التحقق من وجود تسليم سابق"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT assistant, passport, member_name, delivery_date
        FROM deliveries WHERE passport = ?
        ORDER BY delivery_date DESC LIMIT 1
    """, (passport,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "المشرف": row["assistant"],
            "رقم_الجواز": row["passport"],
            "اسم_العضو": row["member_name"],
            "تاريخ_التسليم": row["delivery_date"]
        }
    return None

def get_all_deliveries() -> List[Dict[str, str]]:
    """الحصول على جميع التسليمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT assistant, passport, member_name, delivery_date
        FROM deliveries ORDER BY delivery_date DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "المشرف": row["assistant"],
        "رقم_الجواز": row["passport"],
        "اسم_العضو": row["member_name"],
        "تاريخ_التسليم": row["delivery_date"]
    } for row in rows]

def get_deliveries_by_assistant(assistant: str) -> List[Dict[str, str]]:
    """الحصول على تسليمات مشرف معين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT assistant, passport, member_name, delivery_date
        FROM deliveries WHERE assistant = ?
        ORDER BY delivery_date DESC
    """, (assistant,))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "المشرف": row["assistant"],
        "رقم_الجواز": row["passport"],
        "اسم_العضو": row["member_name"],
        "تاريخ_التسليم": row["delivery_date"]
    } for row in rows]

def delete_all_deliveries() -> bool:
    """حذف جميع التسليمات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM deliveries")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.exception(f"Error deleting deliveries: {e}")
        return False

def get_deliveries_count() -> int:
    """عدد التسليمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM deliveries")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_deliveries_by_assistant_count() -> Dict[str, int]:
    """توزيع التسليمات حسب المشرف"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT assistant, COUNT(*) FROM deliveries GROUP BY assistant")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def get_deliveries_by_date() -> Dict[str, int]:
    """توزيع التسليمات حسب التاريخ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DATE(delivery_date) as date, COUNT(*) 
        FROM deliveries 
        GROUP BY DATE(delivery_date)
        ORDER BY date DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

# =========================
# Services Database Operations
# =========================

def add_service(service_name: str) -> bool:
    """إضافة خدمة جديدة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO services (name) VALUES (?)", (service_name,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.exception(f"Error adding service: {e}")
        return False

def delete_service(service_name: str) -> bool:
    """حذف خدمة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # حذف الخدمة من جدول الخدمات
        cursor.execute("DELETE FROM services WHERE name = ?", (service_name,))
        deleted = cursor.rowcount
        
        # حذف جميع طلبات هذه الخدمة
        cursor.execute("DELETE FROM service_requests WHERE service_name = ?", (service_name,))
        
        conn.commit()
        conn.close()
        return deleted > 0
    except Exception as e:
        logger.exception(f"Error deleting service: {e}")
        return False

def get_all_services() -> List[Dict[str, str]]:
    """الحصول على جميع الخدمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM services ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{"service_id": str(row["id"]), "service_name": row["name"]} for row in rows]

def add_service_request(passport: str, service_name: str, requester: str) -> bool:
    """إضافة طلب خدمة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO service_requests (passport, service_name, requester)
            VALUES (?, ?, ?)
        """, (passport, service_name, requester))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.exception(f"Error adding service request: {e}")
        return False

def check_existing_service_request(passport: str, service_name: str) -> bool:
    """التحقق من وجود طلب خدمة سابق"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM service_requests 
        WHERE passport = ? AND service_name = ?
    """, (passport, service_name))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_service_requests() -> List[Tuple]:
    """الحصول على جميع طلبات الخدمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, passport, service_name, request_date, requester 
        FROM service_requests ORDER BY id
    """)
    rows = cursor.fetchall()
    conn.close()
    return [(row["id"], row["passport"], row["service_name"], row["request_date"], row["requester"]) for row in rows]

def get_service_requests_by_service(service_name: str = None) -> List[Tuple]:
    """الحصول على طلبات خدمة معينة أو جميعها"""
    conn = get_db_connection()
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
    return [(row["id"], row["passport"], row["service_name"], row["request_date"], row["requester"]) for row in rows]

def delete_service_requests_by_service(service_name: str) -> bool:
    """حذف طلبات خدمة معينة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM service_requests WHERE service_name = ?", (service_name,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted > 0
    except Exception as e:
        logger.exception(f"Error deleting service requests: {e}")
        return False

def delete_all_service_requests() -> bool:
    """حذف جميع طلبات الخدمات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM service_requests")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.exception(f"Error deleting all service requests: {e}")
        return False

def get_service_statistics() -> Dict[str, int]:
    """إحصائيات الخدمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT service_name, COUNT(*) 
        FROM service_requests 
        GROUP BY service_name
    """)
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def get_service_requests_count() -> int:
    """عدد طلبات الخدمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM service_requests")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# =========================
# CSV Export functions
# =========================

def export_members_to_csv(filename: str = "members.csv"):
    """تصدير الأعضاء إلى CSV"""
    members = get_all_members()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        if members:
            fieldnames = list(members[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(members)
        else:
            writer = csv.writer(f)
            writer.writerow(["الاسم", "الجواز", "الهاتف", "العنوان", "الصفة", "عدد_افراد_الاسرة"])

def export_assistants_to_csv(filename: str = "assistants.csv"):
    """تصدير المشرفين إلى CSV"""
    assistants = get_all_assistants()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        if assistants:
            fieldnames = list(assistants[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(assistants)
        else:
            writer = csv.writer(f)
            writer.writerow(["username", "password"])

def export_deliveries_to_csv(filename: str = "deliveries.csv"):
    """تصدير التسليمات إلى CSV"""
    deliveries = get_all_deliveries()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        if deliveries:
            fieldnames = list(deliveries[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(deliveries)
        else:
            writer = csv.writer(f)
            writer.writerow(["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"])

def export_assistant_deliveries_to_csv(assistant: str, filename: str):
    """تصدير تسليمات مشرف معين إلى CSV"""
    deliveries = get_deliveries_by_assistant(assistant)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        if deliveries:
            fieldnames = list(deliveries[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(deliveries)
        else:
            writer = csv.writer(f)
            writer.writerow(["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"])

def export_service_requests_to_csv(filename: str = "service_requests.csv", service_name: str = None):
    """تصدير طلبات الخدمات إلى CSV"""
    requests = get_service_requests_by_service(service_name)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"])
        for req in requests:
            writer.writerow(req)

def export_statistics_to_csv(filename: str = "statistics.csv"):
    """تصدير الإحصائيات إلى CSV"""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["نوع الإحصائية", "العدد"])
        writer.writerow(["إجمالي المسجلين", get_members_count()])
        writer.writerow(["إجمالي أفراد الأسر", get_total_family_members()])
        writer.writerow(["إجمالي التسليمات", get_deliveries_count()])
        writer.writerow(["إجمالي المستخدمين", get_users_count()])
        writer.writerow(["إجمالي المشرفين", get_assistants_count()])
        writer.writerow(["إجمالي طلبات الخدمات", get_service_requests_count()])

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
            [KeyboardButton("⬇️ تنزيل البيانات"), KeyboardButton("📤 رفع ملف CSV")],
            [KeyboardButton("📊 ملخص المسجلين"), KeyboardButton("📋 نموذج CSV")],
            [KeyboardButton("🗑️ مسح البيانات"), KeyboardButton("🔙 رجوع")],
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
            [KeyboardButton("📥 تنزيل قائمة المشرفين"), KeyboardButton("🔙 رجوع")],
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

def confirm_csv_upload_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("✅ نعم، أضف البيانات")],
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

def validate_admin_session(context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_type = context.user_data.get("user_type")
    login_user = context.user_data.get("login_user")
    if not user_type or not login_user:
        return False
    if user_type == "main_admin":
        return login_user == ADMIN_USER
    if user_type == "assistant":
        return validate_assistant(login_user, context.user_data.get("login_pass", ""))
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
    
    if add_member(name, passport, phone, address, role, family_count):
        await update.message.reply_text(
            "✅ تم تسجيل بياناتك بنجاح!\n"
            "شكراً لانضمامك إلى منصة الجالية السودانية بأسوان.",
            reply_markup=main_menu_kb()
        )
    else:
        await update.message.reply_text(
            "⚠️ حدث خطأ في التسجيل. يرجى المحاولة مرة أخرى.",
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
        context.user_data["login_pass"] = password
        context.user_data["user_type"] = "main_admin"
        await update.message.reply_text("✅ تم الدخول كمسؤول رئيسي.", reply_markup=admin_menu_kb())
        return States.ADMIN_MENU
    
    if validate_assistant(username, password):
        context.user_data["login_user"] = username
        context.user_data["login_pass"] = password
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
        context.user_data.pop("login_pass", None)
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
    
    users = get_all_users()
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
        services = get_all_services()
        if not services:
            await update.message.reply_text("⚠️ لا توجد خدمات مضافة.", reply_markup=services_admin_kb())
            return States.MANAGE_SERVICES
        
        report = "📋 قائمة الخدمات:\n\n"
        for i, service in enumerate(services, 1):
            report += f"{i}. {service['service_name']}\n"
        
        await update.message.reply_text(report, reply_markup=services_admin_kb())
        return States.MANAGE_SERVICES
    
    elif text == "🗑️ حذف خدمة":
        services = get_all_services()
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
        services = get_all_services()
        
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
    
    if add_service(service_name):
        await update.message.reply_text(
            f"✅ تم إضافة خدمة {service_name} بنجاح.",
            reply_markup=services_admin_kb()
        )
    else:
        await update.message.reply_text(f"⚠️ فشل إضافة الخدمة. قد تكون موجودة مسبقاً.", reply_markup=services_admin_kb())
    
    return States.MANAGE_SERVICES

async def admin_delete_service_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    services = get_all_services()
    if not services:
        await update.message.reply_text("⚠️ لا توجد خدمات لحذفها.", reply_markup=services_admin_kb())
        return States.MANAGE_SERVICES
    
    selected = update.message.text.strip()
    if selected == "🔙 رجوع":
        await update.message.reply_text("⬅️ رجعت لقائمة إدارة الخدمات.", reply_markup=services_admin_kb())
        return States.MANAGE_SERVICES
    
    if delete_service(selected):
        await update.message.reply_text(
            f"✅ تم حذف خدمة {selected} بنجاح.",
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
        services = get_all_services()
        if not services:
            await update.message.reply_text("⚠️ لا توجد خدمات مضافة.", reply_markup=service_report_kb())
            return States.SERVICE_REPORT
        
        await update.message.reply_text("📋 اختر الخدمة للحصول على كشفها:", reply_markup=services_selection_kb(services))
        return States.SELECT_SERVICE_FOR_REPORT
    
    elif text == "📄 كشف لكل الخدمات":
        requests = get_service_requests()
        if not requests:
            await update.message.reply_text("⚠️ لا توجد طلبات خدمات حتى الآن.", reply_markup=service_report_kb())
            return States.SERVICE_REPORT
        
        # إنشاء تقرير شامل
        export_service_requests_to_csv("all_services_report.csv")
        
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
    
    services = get_all_services()
    service_names = [s["service_name"] for s in services]
    
    if selected_service not in service_names:
        await update.message.reply_text("⚠️ الخدمة المختارة غير صحيحة.", reply_markup=services_selection_kb(services))
        return States.SELECT_SERVICE_FOR_REPORT
    
    # إرسال ملف CSV الخاص بالخدمة
    requests = get_service_requests_by_service(selected_service)
    if not requests:
        await update.message.reply_text(f"⚠️ لا توجد طلبات لخدمة {selected_service} حتى الآن.", reply_markup=service_report_kb())
        return States.SERVICE_REPORT
    
    filename = f"{selected_service}_report.csv"
    export_service_requests_to_csv(filename, selected_service)
    
    await update.message.reply_document(
        document=open(filename, "rb"),
        filename=filename,
        caption=f"📄 كشف طلبات خدمة {selected_service}\n"
                f"📊 إجمالي الطلبات: {len(requests)}"
    )
    
    # حذف الملف المؤقت
    os.remove(filename)
    
    await update.message.reply_text("📄 اختر نوع الكشف:", reply_markup=service_report_kb())
    return States.SERVICE_REPORT

# معالجة حذف كشوف الخدمات
async def delete_service_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🗑️ حذف كشف خدمة واحدة":
        services = get_all_services()
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
    
    services = get_all_services()
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
    services = get_all_services()
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
    
    services = get_all_services()
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
    
    if add_service_request(passport, service_name, requester):
        await update.message.reply_text(
            f"✅ تم تقديم طلب {service_name} بنجاح.\n"
            "شكراً لاستخدامك منصة الجالية السودانية بأسوان.",
            reply_markup=main_menu_kb()
        )
    else:
        await update.message.reply_text(
            "⚠️ حدث خطأ في تقديم الطلب. يرجى المحاولة مرة أخرى.",
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
        members_count = get_members_count()
        total_family_members = get_total_family_members()
        deliveries_count = get_deliveries_count()
        users_count = get_users_count()
        assistants_count = get_assistants_count()
        service_requests_count = get_service_requests_count()
        
        report = (
            f"📊 الإحصائيات العامة:\n\n"
            f"👥 إجمالي المسجلين: {members_count}\n"
            f"👨‍👩‍👧‍👦 إجمالي أفراد الأسر: {total_family_members}\n"
            f"📦 إجمالي التسليمات: {deliveries_count}\n"
            f"👤 إجمالي المستخدمين: {users_count}\n"
            f"👮 إجمالي المشرفين: {assistants_count}\n"
            f"📋 إجمالي طلبات الخدمات: {service_requests_count}\n"
        )
        
        await update.message.reply_text(report, reply_markup=stats_choice_kb())
        return States.STATS_MENU
    
    elif text == "📥 تنزيل تقرير CSV":
        export_statistics_to_csv("statistics_report.csv")
        
        await update.message.reply_document(
            document=open("statistics_report.csv", "rb"),
            filename="statistics_report.csv",
            caption="📊 تقرير الإحصائيات"
        )
        
        # حذف الملف المؤقت
        os.remove("statistics_report.csv")
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
        delete_all_deliveries()
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
        members_count = get_members_count()
        if members_count == 0:
            await update.message.reply_text("⚠️ لا توجد بيانات مسجلين حتى الآن.", reply_markup=manage_members_data_kb())
            return States.MANAGE_MEMBERS_DATA
        
        export_members_to_csv("members.csv")
        
        await update.message.reply_document(
            document=open("members.csv", "rb"),
            filename="members.csv",
            caption="📥 بيانات المسجلين"
        )
        
        # حذف الملف المؤقت
        os.remove("members.csv")
        return States.MANAGE_MEMBERS_DATA
    
    elif text == "📤 رفع ملف CSV":
        instructions = (
            "📤 رفع ملف CSV للمسجلين:\n\n"
            "🔹 يجب أن يحتوي الملف على الأعمدة التالية:\n"
            "- الاسم (name)\n"
            "- الجواز (passport)\n"
            "- الهاتف (phone)\n"
            "- العنوان (address)\n"
            "- الصفة (role)\n"
            "- عدد_افراد_الاسرة (family_members)\n\n"
            "🔹 يمكن استخدام الأسماء العربية أو الإنجليزية للأعمدة\n"
            "🔹 للحصول على نموذج، اختر 'نموذج CSV'\n\n"
            "📄 الآن، أرسل ملف CSV:"
        )
        await update.message.reply_text(instructions, reply_markup=cancel_or_back_kb())
        return States.UPLOAD_CSV_FILE
    
    elif text == "📋 نموذج CSV":
        template_file = create_csv_template()
        
        await update.message.reply_document(
            document=open(template_file, "rb"),
            filename="نموذج_المسجلين.csv",
            caption="📋 نموذج ملف CSV للمسجلين\n\n"
                   "يمكنك تعديل البيانات النموذجية وإضافة المزيد من الصفوف"
        )
        
        # حذف الملف المؤقت
        os.remove(template_file)
        return States.MANAGE_MEMBERS_DATA
    
    elif text == "🗑️ مسح البيانات":
        await update.message.reply_text(
            "⚠️ هل أنت متأكد من أنك تريد حذف جميع بيانات المسجلين؟\n\n"
            "هذا الإجراء لا يمكن التراجع عنه.",
            reply_markup=confirm_delete_members_kb(),
        )
        return States.CONFIRM_DELETE_MEMBERS
    
    elif text == "📊 ملخص المسجلين":
        members_count = get_members_count()
        if members_count == 0:
            await update.message.reply_text("⚠️ لا توجد بيانات مسجلين حتى الآن.", reply_markup=manage_members_data_kb())
            return States.MANAGE_MEMBERS_DATA
        
        total_family_members = get_total_family_members()
        roles = get_members_by_role()
        
        report = f"📊 ملخص المسجلين:\n\n"
        report += f"إجمالي المسجلين: {members_count}\n"
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

async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفع ملف CSV"""
    if not update.message.document:
        await update.message.reply_text(
            "⚠️ يرجى إرسال ملف CSV صالح.",
            reply_markup=cancel_or_back_kb()
        )
        return States.UPLOAD_CSV_FILE
    
    # التحقق من نوع الملف
    file_name = update.message.document.file_name
    if not file_name.lower().endswith('.csv'):
        await update.message.reply_text(
            "⚠️ يرجى إرسال ملف CSV فقط.",
            reply_markup=cancel_or_back_kb()
        )
        return States.UPLOAD_CSV_FILE
    
    try:
        # تحميل الملف
        file = await update.message.document.get_file()
        
        # إنشاء ملف مؤقت
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
            await file.download_to_drive(temp_file.name)
            temp_file_path = temp_file.name
        
        # معالجة الملف
        valid_data, errors = process_csv_file(temp_file_path)
        
        # حذف الملف المؤقت
        os.unlink(temp_file_path)
        
        if not valid_data and errors:
            error_message = "❌ فشل في معالجة الملف:\n\n"
            error_message += "\n".join(errors[:10])  # أول 10 أخطاء فقط
            if len(errors) > 10:
                error_message += f"\n... و {len(errors) - 10} خطأ آخر"
            await update.message.reply_text(error_message, reply_markup=cancel_or_back_kb())
            return States.UPLOAD_CSV_FILE
        
        # حفظ البيانات الصالحة في السياق
        context.user_data['csv_data'] = valid_data
        context.user_data['csv_errors'] = errors
        
        # عرض ملخص
        summary = f"📊 ملخص الملف:\n\n"
        summary += f"✅ صفوف صالحة: {len(valid_data)}\n"
        if errors:
            summary += f"⚠️ أخطاء: {len(errors)}\n\n"
            summary += "الأخطاء:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                summary += f"\n... و {len(errors) - 5} خطأ آخر"
        
        summary += f"\n\nهل تريد إضافة {len(valid_data)} عضو إلى النظام؟"
        
        await update.message.reply_text(summary, reply_markup=confirm_csv_upload_kb())
        return States.CONFIRM_CSV_UPLOAD
        
    except Exception as e:
        logger.exception(f"Error processing CSV file: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ في معالجة الملف: {str(e)}",
            reply_markup=cancel_or_back_kb()
        )
        return States.UPLOAD_CSV_FILE

async def confirm_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد إضافة بيانات CSV"""
    text = update.message.text
    
    if text == "✅ نعم، أضف البيانات":
        csv_data = context.user_data.get('csv_data', [])
        if not csv_data:
            await update.message.reply_text(
                "⚠️ لا توجد بيانات للإضافة.",
                reply_markup=manage_members_data_kb()
            )
            return States.MANAGE_MEMBERS_DATA
        
        # إضافة البيانات
        success_count, failed_count, error_messages = add_members_bulk(csv_data)
        
        # رسالة النتيجة
        result_message = f"✅ تم الانتهاء من رفع الملف:\n\n"
        result_message += f"✅ تم إضافة: {success_count} عضو\n"
        if failed_count > 0:
            result_message += f"❌ فشل في إضافة: {failed_count} عضو\n\n"
            if error_messages:
                result_message += "أسباب الفشل:\n"
                result_message += "\n".join(error_messages[:10])
                if len(error_messages) > 10:
                    result_message += f"\n... و {len(error_messages) - 10} خطأ آخر"
        
        await update.message.reply_text(result_message, reply_markup=manage_members_data_kb())
        
    else:
        await update.message.reply_text(
            "❌ تم إلغاء إضافة البيانات.",
            reply_markup=manage_members_data_kb()
        )
    
    # تنظيف البيانات
    context.user_data.pop('csv_data', None)
    context.user_data.pop('csv_errors', None)
    
    return States.MANAGE_MEMBERS_DATA

async def admin_clear_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ نعم، احذف بيانات المسجلين":
        if delete_all_members():
            await update.message.reply_text("🗑️ تم مسح جميع بيانات المسجلين.", reply_markup=manage_members_data_kb())
        else:
            await update.message.reply_text("⚠️ حدث خطأ في مسح البيانات.", reply_markup=manage_members_data_kb())
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
        assistants = get_all_assistants()
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
        assistants = get_all_assistants()
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
        assistants = get_all_assistants()
        if not assistants:
            await update.message.reply_text("⚠️ لا يوجد مشرفين مسجلين.", reply_markup=assistants_management_kb())
            return States.MANAGE_ASSISTANTS
        
        report = "👥 قائمة المشرفين:\n\n"
        for i, assistant in enumerate(assistants, 1):
            report += f"{i}. {assistant['username']}\n"
        
        await update.message.reply_text(report, reply_markup=assistants_management_kb())
        return States.MANAGE_ASSISTANTS
    
    elif text == "📥 تنزيل قائمة المشرفين":
        assistants_count = get_assistants_count()
        if assistants_count == 0:
            await update.message.reply_text("⚠️ لا يوجد مشرفين مسجلين.", reply_markup=assistants_management_kb())
            return States.MANAGE_ASSISTANTS
        
        export_assistants_to_csv("assistants.csv")
        
        await update.message.reply_document(
            document=open("assistants.csv", "rb"),
            filename="assistants.csv",
            caption="📥 قائمة المشرفين"
        )
        
        # حذف الملف المؤقت
        os.remove("assistants.csv")
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
    
    # التحقق من عدم وجود المستخدم مسبقاً
    assistants = get_all_assistants()
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
    
    if add_assistant(new_user, new_pass):
        await update.message.reply_text(
            f"✅ تم إضافة المشرف {new_user} بنجاح.",
            reply_markup=assistants_management_kb()
        )
    else:
        await update.message.reply_text(
            f"⚠️ فشل إضافة المشرف {new_user}.",
            reply_markup=assistants_management_kb()
        )
    
    return States.MANAGE_ASSISTANTS

async def delete_assistant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assistant_to_delete = update.message.text.strip()
    if assistant_to_delete == "🔙 رجوع":
        await update.message.reply_text("تم الإلغاء.", reply_markup=assistants_management_kb())
        return States.MANAGE_ASSISTANTS
    
    if delete_assistant(assistant_to_delete):
        await update.message.reply_text(
            f"✅ تم حذف المشرف {assistant_to_delete} بنجاح.",
            reply_markup=assistants_management_kb()
        )
    else:
        await update.message.reply_text(
            f"⚠️ فشل حذف المشرف {assistant_to_delete}.",
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

async def update_assistant_password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_password = update.message.text.strip()
    if new_password == "🔙 رجوع":
        return await get_new_password_for_assistant(update, context)
    if new_password == "❌ إلغاء":
        await update.message.reply_text("تم الإلغاء.", reply_markup=assistants_management_kb())
        return States.MANAGE_ASSISTANTS
    
    user_to_change = context.user_data.get("change_pass_user")
    
    if update_assistant_password(user_to_change, new_password):
        await update.message.reply_text(
            f"✅ تم تغيير كلمة المرور للمشرف {user_to_change} بنجاح.",
            reply_markup=assistants_management_kb()
        )
    else:
        await update.message.reply_text(
            f"⚠️ فشل تغيير كلمة المرور للمشرف {user_to_change}.",
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
        deliveries_count = get_deliveries_count()
        if deliveries_count == 0:
            await update.message.reply_text("⚠️ لا توجد كشوفات تسليم حتى الآن.", reply_markup=delivery_reports_kb())
            return States.MANAGE_DELIVERY_REPORTS
        
        export_deliveries_to_csv("deliveries.csv")
        
        await update.message.reply_document(
            document=open("deliveries.csv", "rb"),
            filename="deliveries.csv",
            caption="📥 كشوفات التسليم"
        )
        
        # حذف الملف المؤقت
        os.remove("deliveries.csv")
        return States.MANAGE_DELIVERY_REPORTS
    
    elif text == "🗑️ حذف الكشوفات":
        await update.message.reply_text(
            "⚠️ هل أنت متأكد من أنك تريد حذف جميع كشوفات التسليم؟\n\n"
            "هذا الإجراء لا يمكن التراجع عنه.",
            reply_markup=confirm_delete_kb(),
        )
        return States.CONFIRM_DELETE_DELIVERIES
    
    elif text == "📊 عرض الملخص":
        deliveries_count = get_deliveries_count()
        if deliveries_count == 0:
            await update.message.reply_text("⚠️ لا توجد كشوفات تسليم حتى الآن.", reply_markup=delivery_reports_kb())
            return States.MANAGE_DELIVERY_REPORTS
        
        assistants_deliveries = get_deliveries_by_assistant_count()
        
        report = f"📊 ملخص التسليمات:\n\nإجمالي التسليمات: {deliveries_count}\n\nالتوزيع حسب المشرف:\n"
        for assistant, count in assistants_deliveries.items():
            report += f"- {assistant}: {count}\n"
        
        await update.message.reply_text(report, reply_markup=delivery_reports_kb())
        return States.MANAGE_DELIVERY_REPORTS
    
    elif text == "🔙 رجوع":
        await update.message.reply_text("⬅️ رجعت للقائمة الرئيسية للأدمن.", reply_markup=admin_menu_kb())
        return States.ADMIN_MENU
    
    return States.MANAGE_DELIVERY_REPORTS

async def delete_delivery_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ نعم، احذف الكشوفات":
        if delete_all_deliveries():
            await update.message.reply_text("✅ تم حذف جميع كشوفات التسليم.", reply_markup=delivery_reports_kb())
        else:
            await update.message.reply_text("⚠️ حدث خطأ في حذف الكشوفات.", reply_markup=delivery_reports_kb())
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
    
    member = get_member_by_passport(passport)
    
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
        
        if add_delivery(assistant_user, passport, name):
            await update.message.reply_text(
                "✅ تم تسجيل التسليم بنجاح.",
                reply_markup=assistant_menu_kb()
            )
        else:
            await update.message.reply_text(
                "⚠️ حدث خطأ في تسجيل التسليم.",
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
    assistant_deliveries = get_deliveries_by_assistant(assistant_user)
    
    if text == "📥 تحميل":
        if not assistant_deliveries:
            await update.message.reply_text("⚠️ لا توجد تسليمات مسجلة حتى الآن.", reply_markup=assistant_delivery_reports_kb())
            return States.ASSISTANT_VIEW_DELIVERIES
        
        temp_filename = f"{assistant_user}_deliveries.csv"
        export_assistant_deliveries_to_csv(assistant_user, temp_filename)
        
        await update.message.reply_document(
            document=open(temp_filename, "rb"),
            filename=temp_filename,
            caption="📥 كشوفات التسليم"
        )
        
        # حذف الملف المؤقت
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
    init_database()
    
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
            States.CHANGE_ASSISTANT_PASS: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), update_assistant_password_handler)],
            States.MANAGE_MEMBERS_DATA: [MessageHandler(filters.TEXT, manage_members_data_menu)],
            States.UPLOAD_CSV_FILE: [
                MessageHandler(filters.Document.FileExtension("csv"), handle_csv_upload),
                MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), handle_csv_upload)
            ],
            States.CONFIRM_CSV_UPLOAD: [MessageHandler(filters.TEXT, confirm_csv_upload)],
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
        ],
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

if __name__ == "__main__":
    main()
