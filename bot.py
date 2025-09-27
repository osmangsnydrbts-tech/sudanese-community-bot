# -*- coding: utf-8 -*-

import os
import csv
import sqlite3
import logging
from datetime import datetime, date
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple
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

TOKEN = os.getenv('TOKEN')
ADMIN_USER = "Osman"
ADMIN_PASS = "2580"

# قاعدة البيانات الموحدة
DATABASE_FILE = "community_database.db"

# مجلد ملفات CSV المؤقتة
TEMP_CSV_DIR = "temp_csv"

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
    UPLOAD_MEMBERS_CSV_FILE = auto()
    
    # Delivery reports
    MANAGE_DELIVERY_REPORTS = auto()
    CONFIRM_DELETE_DELIVERIES = auto()
    UPLOAD_DELIVERIES_CSV_FILE = auto()
    
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
    UPLOAD_SERVICES_CSV_FILE = auto()
    
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
# Database initialization and helper functions
# =========================

def init_database():
    """تهيئة قاعدة البيانات مع جميع الجداول"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # جدول الأعضاء
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            passport TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            role TEXT,
            family_members INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
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
            supervisor TEXT NOT NULL,
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

def get_db_connection():
    """الحصول على اتصال بقاعدة البيانات"""
    return sqlite3.connect(DATABASE_FILE)

# =========================
# Members functions
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
        logger.error(f"Error adding member: {e}")
        return False

def is_passport_registered(passport: str) -> bool:
    """التحقق من تسجيل رقم الجواز"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM members WHERE passport = ?", (passport,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_member_by_passport(passport: str) -> Optional[Dict]:
    """الحصول على بيانات العضو بواسطة رقم الجواز"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, passport, phone, address, role, family_members, created_at
        FROM members WHERE passport = ?
    """, (passport,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "passport": row[2],
            "phone": row[3],
            "address": row[4],
            "role": row[5],
            "family_members": row[6],
            "created_at": row[7]
        }
    return None

def get_all_members() -> List[Dict]:
    """الحصول على جميع الأعضاء"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, passport, phone, address, role, family_members, created_at
        FROM members ORDER BY id
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "name": row[1],
        "passport": row[2],
        "phone": row[3],
        "address": row[4],
        "role": row[5],
        "family_members": row[6],
        "created_at": row[7]
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
        logger.error(f"Error deleting all members: {e}")
        return False

def export_members_to_csv() -> str:
    """تصدير بيانات الأعضاء إلى CSV"""
    os.makedirs(TEMP_CSV_DIR, exist_ok=True)
    filename = os.path.join(TEMP_CSV_DIR, "members_export.csv")
    
    members = get_all_members()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["الاسم", "الجواز", "الهاتف", "العنوان", "الصفة", "عدد_افراد_الاسرة", "تاريخ_التسجيل"])
        for member in members:
            writer.writerow([
                member["name"], member["passport"], member["phone"],
                member["address"], member["role"], member["family_members"],
                member["created_at"]
            ])
    
    return filename

def validate_members_csv(file_path: str) -> Tuple[bool, str, List[Dict]]:
    """التحقق من صحة ملف CSV للأعضاء"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return False, "❌ الملف فارغ أو لا يحتوي على بيانات", []
        
        required_columns = ["الاسم", "الجواز", "الهاتف", "العنوان", "الصفة", "عدد_افراد_الاسرة"]
        missing_columns = [col for col in required_columns if col not in rows[0].keys()]
        
        if missing_columns:
            return False, f"❌ الأعمدة التالية مفقودة: {', '.join(missing_columns)}", []
        
        valid_rows = []
        errors = []
        
        for i, row in enumerate(rows, 1):
            if not row.get("الاسم") or not row.get("الجواز"):
                errors.append(f"الصف {i}: الاسم ورقم الجواز مطلوبان")
                continue
            
            try:
                family_count = int(row.get("عدد_افراد_الاسرة", "1"))
                if family_count < 1:
                    errors.append(f"الصف {i}: عدد أفراد الأسرة يجب أن يكون أكثر من صفر")
                    continue
            except ValueError:
                errors.append(f"الصف {i}: عدد أفراد الأسرة يجب أن يكون رقماً صحيحاً")
                continue
            
            valid_rows.append({
                "name": row["الاسم"],
                "passport": row["الجواز"],
                "phone": row.get("الهاتف", ""),
                "address": row.get("العنوان", ""),
                "role": row.get("الصفة", ""),
                "family_members": family_count
            })
        
        if errors and len(errors) > 5:
            error_msg = "\n".join(errors[:5]) + f"\n... وغيرها {len(errors) - 5} خطأ"
        elif errors:
            error_msg = "\n".join(errors)
        else:
            error_msg = ""
        
        if errors:
            return False, f"❌ وجدت الأخطاء التالية:\n{error_msg}", valid_rows
        
        return True, f"✅ الملف صالح. عدد السجلات: {len(valid_rows)}", valid_rows
        
    except Exception as e:
        return False, f"❌ خطأ في قراءة الملف: {str(e)}", []

def import_members_from_csv(csv_data: List[Dict]) -> Tuple[int, int, List]:
    """استيراد بيانات الأعضاء من CSV"""
    added_count = 0
    updated_count = 0
    errors = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for i, row in enumerate(csv_data, 1):
        try:
            passport = row["passport"]
            
            # البحث عن العضو الموجود
            cursor.execute("SELECT id FROM members WHERE passport = ?", (passport,))
            existing = cursor.fetchone()
            
            if existing:
                # تحديث العضو الموجود
                cursor.execute("""
                    UPDATE members SET name = ?, phone = ?, address = ?, role = ?, family_members = ?
                    WHERE passport = ?
                """, (row["name"], row["phone"], row["address"], row["role"], row["family_members"], passport))
                updated_count += 1
            else:
                # إضافة عضو جديد
                cursor.execute("""
                    INSERT INTO members (name, passport, phone, address, role, family_members)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (row["name"], passport, row["phone"], row["address"], row["role"], row["family_members"]))
                added_count += 1
                
        except Exception as e:
            errors.append(f"الصف {i}: {str(e)}")
    
    conn.commit()
    conn.close()
    return added_count, updated_count, errors

# =========================
# Users functions
# =========================

def add_user_if_not_exists(user_id: int, username: str):
    """إضافة المستخدم إذا لم يكن موجوداً"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username or ""))
            conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error adding user: {e}")

def get_all_users() -> List[Dict]:
    """الحصول على جميع المستخدمين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, username, created_at FROM users ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "user_id": row[1],
        "username": row[2],
        "created_at": row[3]
    } for row in rows]

# =========================
# Assistants functions
# =========================

def add_assistant(username: str, password: str) -> bool:
    """إضافة مشرف جديد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO assistants (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.error(f"Error adding assistant: {e}")
        return False

def delete_assistant(username: str) -> bool:
    """حذف مشرف"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM assistants WHERE username = ?", (username,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        logger.error(f"Error deleting assistant: {e}")
        return False

def update_assistant_password(username: str, new_password: str) -> bool:
    """تحديث كلمة مرور المشرف"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE assistants SET password = ? WHERE username = ?", (new_password, username))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    except Exception as e:
        logger.error(f"Error updating assistant password: {e}")
        return False

def get_all_assistants() -> List[Dict]:
    """الحصول على جميع المشرفين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password, created_at FROM assistants ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "username": row[1],
        "password": row[2],
        "created_at": row[3]
    } for row in rows]

def validate_assistant(username: str, password: str) -> bool:
    """التحقق من صحة بيانات المشرف"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM assistants WHERE username = ? AND password = ?", (username, password))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def export_assistants_to_csv() -> str:
    """تصدير بيانات المشرفين إلى CSV"""
    os.makedirs(TEMP_CSV_DIR, exist_ok=True)
    filename = os.path.join(TEMP_CSV_DIR, "assistants_export.csv")
    
    assistants = get_all_assistants()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["اسم_المستخدم", "كلمة_المرور", "تاريخ_الإنشاء"])
        for assistant in assistants:
            writer.writerow([assistant["username"], assistant["password"], assistant["created_at"]])
    
    return filename

# =========================
# Deliveries functions
# =========================

def add_delivery(supervisor: str, passport: str, member_name: str, delivery_date: str = None) -> bool:
    """إضافة تسليم جديد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if delivery_date:
            cursor.execute("""
                INSERT INTO deliveries (supervisor, passport, member_name, delivery_date)
                VALUES (?, ?, ?, ?)
            """, (supervisor, passport, member_name, delivery_date))
        else:
            cursor.execute("""
                INSERT INTO deliveries (supervisor, passport, member_name)
                VALUES (?, ?, ?)
            """, (supervisor, passport, member_name))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding delivery: {e}")
        return False

def check_existing_delivery(passport: str) -> Optional[Dict]:
    """البحث عن تسليم موجود"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, supervisor, passport, member_name, delivery_date
        FROM deliveries WHERE passport = ?
        ORDER BY id DESC LIMIT 1
    """, (passport,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "supervisor": row[1],
            "passport": row[2],
            "member_name": row[3],
            "delivery_date": row[4]
        }
    return None

def get_deliveries_by_supervisor(supervisor: str) -> List[Dict]:
    """الحصول على تسليمات المشرف"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, supervisor, passport, member_name, delivery_date
        FROM deliveries WHERE supervisor = ?
        ORDER BY id DESC
    """, (supervisor,))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "supervisor": row[1],
        "passport": row[2],
        "member_name": row[3],
        "delivery_date": row[4]
    } for row in rows]

def get_all_deliveries() -> List[Dict]:
    """الحصول على جميع التسليمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, supervisor, passport, member_name, delivery_date
        FROM deliveries ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row[0],
        "supervisor": row[1],
        "passport": row[2],
        "member_name": row[3],
        "delivery_date": row[4]
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
        logger.error(f"Error deleting all deliveries: {e}")
        return False

def export_deliveries_to_csv() -> str:
    """تصدير التسليمات إلى CSV"""
    os.makedirs(TEMP_CSV_DIR, exist_ok=True)
    filename = os.path.join(TEMP_CSV_DIR, "deliveries_export.csv")
    
    deliveries = get_all_deliveries()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"])
        for delivery in deliveries:
            writer.writerow([delivery["supervisor"], delivery["passport"], delivery["member_name"], delivery["delivery_date"]])
    
    return filename

def validate_deliveries_csv(file_path: str) -> Tuple[bool, str, List[Dict]]:
    """التحقق من صحة ملف CSV للتسليمات"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return False, "❌ الملف فارغ أو لا يحتوي على بيانات", []
        
        required_columns = ["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"]
        missing_columns = [col for col in required_columns if col not in rows[0].keys()]
        
        if missing_columns:
            return False, f"❌ الأعمدة التالية مفقودة: {', '.join(missing_columns)}", []
        
        valid_rows = []
        errors = []
        
        for i, row in enumerate(rows, 1):
            if not row.get("المشرف") or not row.get("رقم_الجواز") or not row.get("اسم_العضو"):
                errors.append(f"الصف {i}: المشرف ورقم الجواز واسم العضو مطلوبان")
                continue
            
            valid_rows.append({
                "supervisor": row["المشرف"],
                "passport": row["رقم_الجواز"],
                "member_name": row["اسم_العضو"],
                "delivery_date": row.get("تاريخ_التسليم", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            })
        
        if errors and len(errors) > 5:
            error_msg = "\n".join(errors[:5]) + f"\n... وغيرها {len(errors) - 5} خطأ"
        elif errors:
            error_msg = "\n".join(errors)
        else:
            error_msg = ""
        
        if errors:
            return False, f"❌ وجدت الأخطاء التالية:\n{error_msg}", valid_rows
        
        return True, f"✅ الملف صالح. عدد السجلات: {len(valid_rows)}", valid_rows
        
    except Exception as e:
        return False, f"❌ خطأ في قراءة الملف: {str(e)}", []

def import_deliveries_from_csv(csv_data: List[Dict]) -> Tuple[int, List]:
    """استيراد التسليمات من CSV"""
    added_count = 0
    errors = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for i, row in enumerate(csv_data, 1):
        try:
            cursor.execute("""
                INSERT INTO deliveries (supervisor, passport, member_name, delivery_date)
                VALUES (?, ?, ?, ?)
            """, (row["supervisor"], row["passport"], row["member_name"], row["delivery_date"]))
            added_count += 1
        except Exception as e:
            errors.append(f"الصف {i}: {str(e)}")
    
    conn.commit()
    conn.close()
    return added_count, errors

# =========================
# Services functions
# =========================

def add_service_to_db(service_name: str) -> bool:
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
        logger.error(f"Error adding service to DB: {e}")
        return False

def delete_service_from_db(service_name: str) -> bool:
    """حذف خدمة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM services WHERE name = ?", (service_name,))
        deleted = cursor.rowcount > 0
        
        cursor.execute("DELETE FROM service_requests WHERE service_name = ?", (service_name,))
        
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        logger.error(f"Error deleting service from DB: {e}")
        return False

def get_services_from_db() -> List[Dict]:
    """الحصول على جميع الخدمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM services ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{
        "service_id": str(row[0]),
        "service_name": row[1],
        "created_at": row[2]
    } for row in rows]

def add_service_request(passport: str, service_name: str, requester: str, request_date: str = None):
    """إضافة طلب خدمة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if request_date:
            cursor.execute("""
                INSERT INTO service_requests (passport, service_name, requester, request_date)
                VALUES (?, ?, ?, ?)
            """, (passport, service_name, requester, request_date))
        else:
            cursor.execute("""
                INSERT INTO service_requests (passport, service_name, requester)
                VALUES (?, ?, ?)
            """, (passport, service_name, requester))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.exception("Error inserting service request")

def get_service_requests_from_db() -> List[Tuple]:
    """الحصول على جميع طلبات الخدمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, passport, service_name, request_date, requester
        FROM service_requests ORDER BY id
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_service_requests_by_service(service_name: str = None) -> List[Tuple]:
    """الحصول على طلبات خدمة معينة"""
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
    return rows

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
        logger.error(f"Error deleting all service requests from DB: {e}")
        return False

def delete_service_requests_by_service(service_name: str) -> bool:
    """حذف طلبات خدمة معينة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM service_requests WHERE service_name = ?", (service_name,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        logger.error(f"Error deleting service requests by service: {e}")
        return False

def check_existing_service_request(passport: str, service_name: str) -> bool:
    """التحقق من وجود طلب خدمة مسبق"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM service_requests 
        WHERE passport = ? AND service_name = ?
    """, (passport, service_name))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_service_statistics() -> Dict[str, int]:
    """إحصائيات الخدمات"""
    services = get_services_from_db()
    stats = {}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for service in services:
        service_name = service["service_name"]
        cursor.execute("SELECT COUNT(*) FROM service_requests WHERE service_name = ?", (service_name,))
        count = cursor.fetchone()[0]
        stats[service_name] = count
    
    conn.close()
    return stats

def export_service_requests_to_csv(service_name: str = None) -> str:
    """تصدير طلبات الخدمات إلى CSV"""
    os.makedirs(TEMP_CSV_DIR, exist_ok=True)
    
    if service_name:
        filename = os.path.join(TEMP_CSV_DIR, f"service_requests_{service_name}.csv")
        requests = get_service_requests_by_service(service_name)
    else:
        filename = os.path.join(TEMP_CSV_DIR, "all_service_requests.csv")
        requests = get_service_requests_by_service()
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"])
        for request in requests:
            writer.writerow([request[1], request[2], request[3], request[4]])
    
    return filename

def validate_service_requests_csv(file_path: str) -> Tuple[bool, str, List[Dict]]:
    """التحقق من صحة ملف CSV لطلبات الخدمات"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return False, "❌ الملف فارغ أو لا يحتوي على بيانات", []
        
        required_columns = ["رقم_الجواز", "الخدمة", "تاريخ_الطلب", "مقدم_الطلب"]
        missing_columns = [col for col in required_columns if col not in rows[0].keys()]
        
        if missing_columns:
            return False, f"❌ الأعمدة التالية مفقودة: {', '.join(missing_columns)}", []
        
        valid_rows = []
        errors = []
        
        for i, row in enumerate(rows, 1):
            if not row.get("رقم_الجواز") or not row.get("الخدمة") or not row.get("مقدم_الطلب"):
                errors.append(f"الصف {i}: رقم الجواز والخدمة ومقدم الطلب مطلوبان")
                continue
            
            valid_rows.append({
                "passport": row["رقم_الجواز"],
                "service_name": row["الخدمة"],
                "request_date": row.get("تاريخ_الطلب", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "requester": row["مقدم_الطلب"]
            })
        
        if errors and len(errors) > 5:
            error_msg = "\n".join(errors[:5]) + f"\n... وغيرها {len(errors) - 5} خطأ"
        elif errors:
            error_msg = "\n".join(errors)
        else:
            error_msg = ""
        
        if errors:
            return False, f"❌ وجدت الأخطاء التالية:\n{error_msg}", valid_rows
        
        return True, f"✅ الملف صالح. عدد السجلات: {len(valid_rows)}", valid_rows
        
    except Exception as e:
        return False, f"❌ خطأ في قراءة الملف: {str(e)}", []

def import_service_requests_from_csv(csv_data: List[Dict]) -> Tuple[int, List]:
    """استيراد طلبات الخدمات من CSV"""
    added_count = 0
    errors = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for i, row in enumerate(csv_data, 1):
        try:
            cursor.execute("""
                INSERT INTO service_requests (passport, service_name, request_date, requester)
                VALUES (?, ?, ?, ?)
            """, (row["passport"], row["service_name"], row["request_date"], row["requester"]))
            added_count += 1
        except Exception as e:
            errors.append(f"الصف {i}: {str(e)}")
    
    conn.commit()
    conn.close()
    return added_count, errors

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
            [KeyboardButton("📤 رفع ملف CSV"), KeyboardButton("📊 ملخص المسجلين")],
            [KeyboardButton("🔙 رجوع")],
        ],
        resize_keyboard=True,
    )

def upload_csv_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("❌ إلغاء الرفع")],
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
            [KeyboardButton("📤 رفع ملف CSV"), KeyboardButton("📊 عرض الملخص")],
            [KeyboardButton("🔙 رجوع")],
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
            [KeyboardButton("📤 رفع ملف CSV"), KeyboardButton("🗑️ حذف كشوف الخدمات")],
            [KeyboardButton("🔙 رجوع")],
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
    """التحقق من صحة جلسة الأدمن"""
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
    """تنسيق رقم الهاتف لرابط الواتساب"""
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
            "❌ حدث خطأ في التسجيل. يرجى المحاولة مرة أخرى.",
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
# إدارة بيانات الأعضاء مع رفع CSV
# =========================

async def manage_members_data_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not validate_admin_session(context) or context.user_data.get("user_type") != "main_admin":
        await update.message.reply_text("⚠️ ليس لديك صلاحيات الوصول.", reply_markup=main_menu_kb())
        return ConversationHandler.END
    
    text = update.message.text
    
    if text == "⬇️ تنزيل البيانات":
        members = get_all_members()
        if not members:
            await update.message.reply_text("⚠️ لا توجد بيانات مسجلين حتى الآن.", reply_markup=manage_members_data_kb())
            return States.MANAGE_MEMBERS_DATA
        
        filename = export_members_to_csv()
        await update.message.reply_document(
            document=open(filename, "rb"),
            filename="members.csv",
            caption="📥 بيانات المسجلين"
        )
        os.remove(filename)
        return States.MANAGE_MEMBERS_DATA
    
    elif text == "🗑️ مسح البيانات":
        await update.message.reply_text(
            "⚠️ هل أنت متأكد من أنك تريد حذف جميع بيانات المسجلين؟\n\n"
            "هذا الإجراء لا يمكن التراجع عنه.",
            reply_markup=confirm_delete_members_kb(),
        )
        return States.CONFIRM_DELETE_MEMBERS
    
    elif text == "📤 رفع ملف CSV":
        await update.message.reply_text(
            "📤 أرسل ملف CSV الذي يحتوي على بيانات الأعضاء.\n\n"
            "⚠️ يجب أن يحتوي الملف على الأعمدة التالية:\n"
            "• الاسم\n• الجواز\n• الهاتف\n• العنوان\n• الصفة\n• عدد_افراد_الاسرة\n\n"
            "يمكنك استخدام الزر '⬇️ تنزيل البيانات' لتحميل نموذج الملف.",
            reply_markup=upload_csv_kb()
        )
        return States.UPLOAD_MEMBERS_CSV_FILE
    
    elif text == "📊 ملخص المسجلين":
        members = get_all_members()
        if not members:
            await update.message.reply_text("⚠️ لا توجد بيانات مسجلين حتى الآن.", reply_markup=manage_members_data_kb())
            return States.MANAGE_MEMBERS_DATA
        
        total = len(members)
        total_family_members = sum(member["family_members"] for member in members)
        
        roles = {}
        for member in members:
            role = member.get("role", "غير محدد")
            roles[role] = roles.get(role, 0) + 1
        
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

async def handle_members_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفع ملف CSV للأعضاء"""
    if update.message.document:
        file = await update.message.document.get_file()
        
        os.makedirs(TEMP_CSV_DIR, exist_ok=True)
        file_path = os.path.join(TEMP_CSV_DIR, f"members_upload_{update.update_id}.csv")
        await file.download_to_drive(file_path)
        
        is_valid, message, csv_data = validate_members_csv(file_path)
        
        if not is_valid:
            os.remove(file_path)
            await update.message.reply_text(
                f"{message}\n\nيرجى تصحيح الأخطاء وإعادة الرفع.",
                reply_markup=manage_members_data_kb()
            )
            return States.MANAGE_MEMBERS_DATA
        
        added_count, updated_count, errors = import_members_from_csv(csv_data)
        
        os.remove(file_path)
        
        result_message = f"✅ تم تحديث البيانات بنجاح!\n\n"
        result_message += f"📊 النتائج:\n"
        result_message += f"• عدد السجلات المضافة: {added_count}\n"
        result_message += f"• عدد السجلات المحدثة: {updated_count}\n"
        result_message += f"• إجمالي السجلات: {added_count + updated_count}\n"
        
        if errors:
            result_message += f"\n⚠️ ملاحظات:\n"
            for error in errors[:3]:
                result_message += f"• {error}\n"
            if len(errors) > 3:
                result_message += f"• ... وغيرها {len(errors) - 3} ملاحظة\n"
        
        await update.message.reply_text(result_message, reply_markup=manage_members_data_kb())
        return States.MANAGE_MEMBERS_DATA
    
    elif update.message.text == "❌ إلغاء الرفع":
        await update.message.reply_text("❌ تم إلغاء عملية الرفع.", reply_markup=manage_members_data_kb())
        return States.MANAGE_MEMBERS_DATA
    else:
        await update.message.reply_text(
            "📤 يرجى إرسال ملف CSV أو الضغط على '❌ إلغاء الرفع' للإلغاء.",
            reply_markup=upload_csv_kb()
        )
        return States.UPLOAD_MEMBERS_CSV_FILE

async def admin_clear_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ نعم، احذف بيانات المسجلين":
        if delete_all_members():
            await update.message.reply_text("🗑️ تم مسح جميع بيانات المسجلين.", reply_markup=manage_members_data_kb())
        else:
            await update.message.reply_text("❌ حدث خطأ في حذف البيانات.", reply_markup=manage_members_data_kb())
    else:
        await update.message.reply_text("❌ تم إلغاء حذف البيانات.", reply_markup=manage_members_data_kb())
    return States.MANAGE_MEMBERS_DATA

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
            f"✅ تم إضافة خدمة {service_name} بنجاح.",
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
        
        filename = export_service_requests_to_csv()
        await update.message.reply_document(
            document=open(filename, "rb"),
            filename="all_services_report.csv",
            caption="📄 كشف جميع طلبات الخدمات"
        )
        os.remove(filename)
        return States.SERVICE_REPORT
    
    elif text == "📤 رفع ملف CSV":
        await update.message.reply_text(
            "📤 أرسل ملف CSV الذي يحتوي على طلبات الخدمات.\n\n"
            "⚠️ يجب أن يحتوي الملف على الأعمدة التالية:\n"
            "• رقم_الجواز\n• الخدمة\n• تاريخ_الطلب\n• مقدم_الطلب",
            reply_markup=upload_csv_kb()
        )
        return States.UPLOAD_SERVICES_CSV_FILE
    
    elif text == "🗑️ حذف كشوف الخدمات":
        await update.message.reply_text("🗑️ اختر نوع الحذف:", reply_markup=service_delete_report_kb())
        return States.DELETE_SERVICE_REPORT
    
    elif text == "🔙 رجوع":
        await update.message.reply_text("⬅️ رجعت لقائمة إدارة الخدمات.", reply_markup=services_admin_kb())
        return States.MANAGE_SERVICES
    
    return States.SERVICE_REPORT

async def handle_services_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفع ملف CSV لطلبات الخدمات"""
    if update.message.document:
        file = await update.message.document.get_file()
        
        os.makedirs(TEMP_CSV_DIR, exist_ok=True)
        file_path = os.path.join(TEMP_CSV_DIR, f"services_upload_{update.update_id}.csv")
        await file.download_to_drive(file_path)
        
        is_valid, message, csv_data = validate_service_requests_csv(file_path)
        
        if not is_valid:
            os.remove(file_path)
            await update.message.reply_text(
                f"{message}\n\nيرجى تصحيح الأخطاء وإعادة الرفع.",
                reply_markup=service_report_kb()
            )
            return States.SERVICE_REPORT
        
        added_count, errors = import_service_requests_from_csv(csv_data)
        
        os.remove(file_path)
        
        result_message = f"✅ تم رفع البيانات بنجاح!\n\n"
        result_message += f"📊 النتائج:\n"
        result_message += f"• عدد الطلبات المضافة: {added_count}\n"
        
        if errors:
            result_message += f"\n⚠️ ملاحظات:\n"
            for error in errors[:3]:
                result_message += f"• {error}\n"
            if len(errors) > 3:
                result_message += f"• ... وغيرها {len(errors) - 3} ملاحظة\n"
        
        await update.message.reply_text(result_message, reply_markup=service_report_kb())
        return States.SERVICE_REPORT
    
    elif update.message.text == "❌ إلغاء الرفع":
        await update.message.reply_text("❌ تم إلغاء عملية الرفع.", reply_markup=service_report_kb())
        return States.SERVICE_REPORT
    else:
        await update.message.reply_text(
            "📤 يرجى إرسال ملف CSV أو الضغط على '❌ إلغاء الرفع' للإلغاء.",
            reply_markup=upload_csv_kb()
        )
        return States.UPLOAD_SERVICES_CSV_FILE

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
    
    requests = get_service_requests_by_service(selected_service)
    if not requests:
        await update.message.reply_text(f"⚠️ لا توجد طلبات لخدمة {selected_service} حتى الآن.", reply_markup=service_report_kb())
        return States.SERVICE_REPORT
    
    filename = export_service_requests_to_csv(selected_service)
    await update.message.reply_document(
        document=open(filename, "rb"),
        filename=f"{selected_service}_report.csv",
        caption=f"📄 كشف طلبات خدمة {selected_service}\n"
                f"📊 إجمالي الطلبات: {len(requests)}"
    )
    os.remove(filename)
    
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
    
    requester = member.get("name", "غير مسجل")
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
        members = get_all_members()
        deliveries = get_all_deliveries()
        users = get_all_users()
        assistants = get_all_assistants()
        service_requests = get_service_requests_from_db()
        
        total_family_members = sum(member["family_members"] for member in members)
        
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
        members = get_all_members()
        deliveries = get_all_deliveries()
        users = get_all_users()
        assistants = get_all_assistants()
        service_requests = get_service_requests_from_db()
        
        total_family_members = sum(member["family_members"] for member in members)
        
        os.makedirs(TEMP_CSV_DIR, exist_ok=True)
        stats_filename = os.path.join(TEMP_CSV_DIR, "statistics_report.csv")
        
        with open(stats_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["نوع الإحصائية", "العدد"])
            writer.writerow(["إجمالي المسجلين", len(members)])
            writer.writerow(["إجمالي أفراد الأسر", total_family_members])
            writer.writerow(["إجمالي التسليمات", len(deliveries)])
            writer.writerow(["إجمالي المستخدمين", len(users)])
            writer.writerow(["إجمالي المشرفين", len(assistants)])
            writer.writerow(["إجمالي طلبات الخدمات", len(service_requests)])
        
        await update.message.reply_document(
            document=open(stats_filename, "rb"),
            filename="statistics_report.csv",
            caption="📊 تقرير الإحصائيات"
        )
        os.remove(stats_filename)
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
        success = True
        if not delete_all_deliveries():
            success = False
        if not delete_all_service_requests():
            success = False
        
        if success:
            await update.message.reply_text("✅ تم حذف جميع الإحصائيات.", reply_markup=stats_choice_kb())
        else:
            await update.message.reply_text("⚠️ حدث خطأ في حذف بعض الإحصائيات.", reply_markup=stats_choice_kb())
    else:
        await update.message.reply_text("❌ تم إلغاء حذف الإحصائيات.", reply_markup=stats_choice_kb())
    return States.STATS_MENU

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
        assistants = get_all_assistants()
        if not assistants:
            await update.message.reply_text("⚠️ لا يوجد مشرفين مسجلين.", reply_markup=assistants_management_kb())
            return States.MANAGE_ASSISTANTS
        
        filename = export_assistants_to_csv()
        await update.message.reply_document(
            document=open(filename, "rb"),
            filename="assistants.csv",
            caption="📥 قائمة المشرفين"
        )
        os.remove(filename)
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
            f"❌ فشل إضافة المشرف {new_user}.",
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
            f"❌ فشل حذف المشرف {assistant_to_delete}.",
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
            f"❌ فشل تغيير كلمة المرور للمشرف {user_to_change}.",
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
        deliveries = get_all_deliveries()
        if not deliveries:
            await update.message.reply_text("⚠️ لا توجد كشوفات تسليم حتى الآن.", reply_markup=delivery_reports_kb())
            return States.MANAGE_DELIVERY_REPORTS
        
        filename = export_deliveries_to_csv()
        await update.message.reply_document(
            document=open(filename, "rb"),
            filename="deliveries.csv",
            caption="📥 كشوفات التسليم"
        )
        os.remove(filename)
        return States.MANAGE_DELIVERY_REPORTS
    
    elif text == "🗑️ حذف الكشوفات":
        await update.message.reply_text(
            "⚠️ هل أنت متأكد من أنك تريد حذف جميع كشوفات التسليم؟\n\n"
            "هذا الإجراء لا يمكن التراجع عنه.",
            reply_markup=confirm_delete_kb(),
        )
        return States.CONFIRM_DELETE_DELIVERIES
    
    elif text == "📤 رفع ملف CSV":
        await update.message.reply_text(
            "📤 أرسل ملف CSV الذي يحتوي على بيانات التسليمات.\n\n"
            "⚠️ يجب أن يحتوي الملف على الأعمدة التالية:\n"
            "• المشرف\n• رقم_الجواز\n• اسم_العضو\n• تاريخ_التسليم",
            reply_markup=upload_csv_kb()
        )
        return States.UPLOAD_DELIVERIES_CSV_FILE
    
    elif text == "📊 عرض الملخص":
        deliveries = get_all_deliveries()
        if not deliveries:
            await update.message.reply_text("⚠️ لا توجد كشوفات تسليم حتى الآن.", reply_markup=delivery_reports_kb())
            return States.MANAGE_DELIVERY_REPORTS
        
        total = len(deliveries)
        assistants = {}
        for delivery in deliveries:
            assistant = delivery.get("supervisor", "غير معروف")
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

async def handle_deliveries_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفع ملف CSV للتسليمات"""
    if update.message.document:
        file = await update.message.document.get_file()
        
        os.makedirs(TEMP_CSV_DIR, exist_ok=True)
        file_path = os.path.join(TEMP_CSV_DIR, f"deliveries_upload_{update.update_id}.csv")
        await file.download_to_drive(file_path)
        
        is_valid, message, csv_data = validate_deliveries_csv(file_path)
        
        if not is_valid:
            os.remove(file_path)
            await update.message.reply_text(
                f"{message}\n\nيرجى تصحيح الأخطاء وإعادة الرفع.",
                reply_markup=delivery_reports_kb()
            )
            return States.MANAGE_DELIVERY_REPORTS
        
        added_count, errors = import_deliveries_from_csv(csv_data)
        
        os.remove(file_path)
        
        result_message = f"✅ تم رفع البيانات بنجاح!\n\n"
        result_message += f"📊 النتائج:\n"
        result_message += f"• عدد التسليمات المضافة: {added_count}\n"
        
        if errors:
            result_message += f"\n⚠️ ملاحظات:\n"
            for error in errors[:3]:
                result_message += f"• {error}\n"
            if len(errors) > 3:
                result_message += f"• ... وغيرها {len(errors) - 3} ملاحظة\n"
        
        await update.message.reply_text(result_message, reply_markup=delivery_reports_kb())
        return States.MANAGE_DELIVERY_REPORTS
    
    elif update.message.text == "❌ إلغاء الرفع":
        await update.message.reply_text("❌ تم إلغاء عملية الرفع.", reply_markup=delivery_reports_kb())
        return States.MANAGE_DELIVERY_REPORTS
    else:
        await update.message.reply_text(
            "📤 يرجى إرسال ملف CSV أو الضغط على '❌ إلغاء الرفع' للإلغاء.",
            reply_markup=upload_csv_kb()
        )
        return States.UPLOAD_DELIVERIES_CSV_FILE

async def delete_delivery_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ نعم، احذف الكشوفات":
        if delete_all_deliveries():
            await update.message.reply_text("✅ تم حذف جميع كشوفات التسليم.", reply_markup=delivery_reports_kb())
        else:
            await update.message.reply_text("❌ حدث خطأ في حذف الكشوفات.", reply_markup=delivery_reports_kb())
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
            f"⚠️ تحذير: العضو {member.get('name')} تم تسليمه من قبل!\n\n"
            f"المشرف: {existing_delivery.get('supervisor')}\n"
            f"التاريخ: {existing_delivery.get('delivery_date')}\n\n"
            f"هل تريد تسليمه مرة أخرى؟"
        )
        context.user_data["pending_delivery_passport"] = passport
        context.user_data["pending_delivery_name"] = member.get("name")
        
        await update.message.reply_text(warning_message, reply_markup=confirm_delivery_kb())
        return States.CONFIRM_DELIVERY
    
    context.user_data["pending_delivery_passport"] = passport
    context.user_data["pending_delivery_name"] = member.get("name")
    
    await update.message.reply_text(
        f"✅ تم العثور على العضو: {member.get('name')}\n"
        f"📞 الهاتف: {member.get('phone')}\n\n"
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
                "❌ حدث خطأ في تسجيل التسليم.",
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
    assistant_deliveries = get_deliveries_by_supervisor(assistant_user)
    
    if text == "📥 تحميل":
        if not assistant_deliveries:
            await update.message.reply_text("⚠️ لا توجد تسليمات مسجلة حتى الآن.", reply_markup=assistant_delivery_reports_kb())
            return States.ASSISTANT_VIEW_DELIVERIES
        
        os.makedirs(TEMP_CSV_DIR, exist_ok=True)
        temp_filename = os.path.join(TEMP_CSV_DIR, f"{assistant_user}_deliveries.csv")
        
        with open(temp_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["المشرف", "رقم_الجواز", "اسم_العضو", "تاريخ_التسليم"])
            for delivery in assistant_deliveries:
                writer.writerow([delivery["supervisor"], delivery["passport"], delivery["member_name"], delivery["delivery_date"]])
        
        await update.message.reply_document(
            document=open(temp_filename, "rb"),
            filename=f"{assistant_user}_deliveries.csv",
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
            date_str = delivery.get("delivery_date", "").split(" ")[0]
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
    
    # إنشاء مجلد CSV المؤقت
    os.makedirs(TEMP_CSV_DIR, exist_ok=True)
    
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
            States.UPLOAD_MEMBERS_CSV_FILE: [MessageHandler(filters.ALL, handle_members_csv_upload)],
            States.CONFIRM_DELETE_MEMBERS: [MessageHandler(filters.TEXT, admin_clear_members)],
            States.MANAGE_DELIVERY_REPORTS: [MessageHandler(filters.TEXT, manage_delivery_reports_menu)],
            States.UPLOAD_DELIVERIES_CSV_FILE: [MessageHandler(filters.ALL, handle_deliveries_csv_upload)],
            States.CONFIRM_DELETE_DELIVERIES: [MessageHandler(filters.TEXT, delete_delivery_reports)],
            States.STATS_MENU: [MessageHandler(filters.TEXT, admin_stats_choice_handler)],
            States.CONFIRM_DELETE_STATS: [MessageHandler(filters.TEXT, admin_delete_stats)],
            States.MANAGE_SERVICES: [MessageHandler(filters.TEXT, manage_services_menu)],
            States.ADD_SERVICE: [MessageHandler(filters.TEXT & ~filters.Text(["❌ إلغاء", "🔙 رجوع"]), admin_add_service_start)],
            States.DELETE_SERVICE: [MessageHandler(filters.TEXT & ~filters.Text(["🔙 رجوع"]), admin_delete_service_start)],
            States.SERVICE_REPORT: [MessageHandler(filters.TEXT, service_report_handler)],
            States.UPLOAD_SERVICES_CSV_FILE: [MessageHandler(filters.ALL, handle_services_csv_upload)],
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
    print("🚀 البوت يعمل الآن بقاعدة بيانات SQLite...")
    application.run_polling()

if __name__ == "__main__":
    main()
