#!/usr/bin/env python3
"""
🤖 ربات تریدر هوش مصنوعی V3.0 - Ultimate Trading Bot
نسخه کامل و بهینه‌شده برای ریلیوی
"""

import os
import sys
import uuid
import time
import json
import math
import logging
import sqlite3
import asyncio
import hashlib
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from contextlib import closing

import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ============================================
# ⚙️ CONFIGURATION - تنظیمات اصلی
# ============================================

# 🔐 توکن تلگرام و ادمین (سخت‌کد شده در کد)
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
SECOND_ADMIN_ID = 5993860770

# 📁 مسیرهای فایل
DB_PATH = "trading_brain_v3.db"
LOG_FILE = "trading_bot.log"
BACKUP_DIR = "backups/"
CHART_DIR = "charts/"

# ⏱ تنظیمات زمانی
ANALYSIS_TIMEFRAME = "1h"
ANALYSIS_PERIOD = "30d"
UPDATE_INTERVAL = 0.5  # زمان بین آپدیت‌ها
MAX_RETRIES = 5
RETRY_DELAY = 2

# 📊 تنظیمات تحلیل
MIN_WIN_RATE = 60
MAX_SIGNALS_PER_DAY = 15
RISK_PER_TRADE = 0.02  # 2% ریسک در هر معامله

# 🪙 لیست کامل ارزهای پشتیبانی شده
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 
    'ETH/USDT': 'ETH-USD', 
    'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 
    'XRP/USDT': 'XRP-USD',
    'ADA/USDT': 'ADA-USD',
    'AVAX/USDT': 'AVAX-USD',
    'DOGE/USDT': 'DOGE-USD', 
    'DOT/USDT': 'DOT-USD',
    'LINK/USDT': 'LINK-USD',
    'MATIC/USDT': 'MATIC-USD',
    'SHIB/USDT': 'SHIB-USD',
    'TRX/USDT': 'TRX-USD',
    'UNI/USDT': 'UNI-USD',
    'ATOM/USDT': 'ATOM-USD',
    'TON/USDT': 'TON-USD',
    'PEPE/USDT': 'PEPE-USD',
    'SUI/USDT': 'SUI-USD',
    'APT/USDT': 'APT-USD',
    'ARB/USDT': 'ARB-USD',
    'OP/USDT': 'OP-USD',
    'NEAR/USDT': 'NEAR-USD',
    'LTC/USDT': 'LTC-USD',
    'BCH/USDT': 'BCH-USD',
    'FIL/USDT': 'FIL-USD',
    'ETC/USDT': 'ETC-USD'
}

# ============================================
# 🪵 LOGGING SETUP - تنظیمات لاگ
# ============================================

def setup_logging():
    """تنظیمات پیشرفته لاگ‌گیری"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # فرمت لاگ
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # هندلر کنسول
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # هندلر فایل
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # اضافه کردن هندلرها
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # غیرفعال کردن لاگ‌های کتابخانه‌های خارجی
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    
    return logger

logger = setup_logging()

# ============================================
# 🗄️ DATABASE MANAGER - مدیریت دیتابیس
# ============================================

class DatabaseManager:
    """مدیریت پیشرفته دیتابیس SQLite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
        logger.info(f"📦 دیتابیس در {db_path} راه‌اندازی شد")
    
    def get_connection(self) -> sqlite3.Connection:
        """ایجاد اتصال به دیتابیس"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
    
    def init_database(self):
        """ایجاد جداول دیتابیس"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول کاربران
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    expiry REAL DEFAULT 0,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_signals INTEGER DEFAULT 0,
                    successful_signals INTEGER DEFAULT 0,
                    failed_signals INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    is_premium INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'fa',
                    settings TEXT DEFAULT '{}'
                )
            ''')
            
            # جدول لایسنس‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY,
                    days INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_by TEXT,
                    used_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    license_type TEXT DEFAULT 'regular'
                )
            ''')
            
            # جدول سیگنال‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    win_probability REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    generated_by TEXT DEFAULT 'BOT',
                    is_vip INTEGER DEFAULT 0,
                    result TEXT,
                    closed_at TIMESTAMP,
                    profit_loss REAL,
                    risk_reward_ratio REAL,
                    signal_type TEXT,
                    confidence TEXT
                )
            ''')
            
            # جدول تراکنش‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USDT',
                    tx_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    details TEXT
                )
            ''')
            
            # جدول لاگ فعالیت‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول تنظیمات سیستم
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ایجاد ایندکس‌ها
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_expiry ON users(expiry)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_user_time ON activity_logs(user_id, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_licenses_active ON licenses(is_active)')
            
            # تنظیمات اولیه سیستم
            default_settings = [
                ('app_name', 'AI Trading Bot V3.0', 'نام برنامه'),
                ('version', '3.0.0', 'ورژن برنامه'),
                ('min_win_rate', '60', 'حداقل درصد برد برای سیگنال'),
                ('max_signals_daily', '15', 'حداکثر سیگنال روزانه'),
                ('risk_per_trade', '0.02', 'ریسک در هر معامله'),
                ('maintenance_mode', '0', 'حالت تعمیرات'),
                ('broadcast_message', '', 'پیام همگانی')
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO system_settings (key, value, description) 
                VALUES (?, ?, ?)
            ''', default_settings)
            
            conn.commit()
            logger.info("✅ جداول دیتابیس ایجاد/بررسی شدند")
    
    def log_activity(self, user_id: str, action: str, details: str = "", 
                    ip_address: str = "", user_agent: str = ""):
        """ثبت فعالیت کاربر در سیستم"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO activity_logs 
                (user_id, action, details, ip_address, user_agent) 
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action, details, ip_address, user_agent))
            conn.commit()
    
    def add_user(self, user_id: str, username: str = "", 
                first_name: str = "", last_name: str = "", 
                expiry: float = 0, role: str = 'user'):
        """اضافه کردن کاربر جدید"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, expiry, role, last_active) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, expiry, role, time.time()))
            conn.commit()
            self.log_activity(user_id, "USER_REGISTER", 
                            f"New user registered with role: {role}")
            logger.info(f"👤 کاربر جدید اضافه شد: {user_id}")
    
    def get_user(self, user_id: str) -> Optional[sqlite3.Row]:
        """دریافت اطلاعات کاربر"""
        with self.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?", 
                (user_id,)
            ).fetchone()
    
    def update_user_activity(self, user_id: str):
        """بروزرسانی زمان آخرین فعالیت کاربر"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (time.time(), user_id)
            )
            conn.commit()
    
    def create_license(self, days: int, license_type: str = "regular") -> str:
        """ایجاد لایسنس جدید"""
        license_key = f"VIP-{uuid.uuid4().hex[:6].upper()}-{days}D"
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO licenses (license_key, days, license_type) 
                VALUES (?, ?, ?)
            ''', (license_key, days, license_type))
            conn.commit()
            self.log_activity("SYSTEM", "LICENSE_CREATED", 
                            f"Created {days}-day {license_type} license: {license_key}")
            logger.info(f"🔑 لایسنس جدید ایجاد شد: {license_key} ({days} روز)")
        return license_key
    
    def activate_license(self, license_key: str, user_id: str) -> Tuple[bool, str]:
        """فعال‌سازی لایسنس"""
        with self.get_connection() as conn:
            # بررسی لایسنس
            license_data = conn.execute(
                '''SELECT days, is_active, license_type 
                   FROM licenses WHERE license_key = ?''',
                (license_key,)
            ).fetchone()
            
            if not license_data:
                return False, "❌ لایسنس یافت نشد"
            
            if license_data['is_active'] == 0:
                return False, "❌ این لایسنس قبلاً استفاده شده است"
            
            days = license_data['days']
            license_type = license_data['license_type']
            
            # محاسبه تاریخ انقضا
            user = self.get_user(user_id)
            current_time = time.time()
            
            if user and user['expiry'] > current_time:
                # تمدید اشتراک
                new_expiry = user['expiry'] + (days * 86400)
                message = f"✅ اشتراک شما {days} روز تمدید شد!"
            else:
                # اشتراک جدید
                new_expiry = current_time + (days * 86400)
                message = f"✅ اشتراک {days} روزه با موفقیت فعال شد!"
            
            # بروزرسانی لایسنس
            conn.execute('''
                UPDATE licenses 
                SET used_by = ?, used_at = ?, is_active = 0 
                WHERE license_key = ?
            ''', (user_id, datetime.now().isoformat(), license_key))
            
            # بروزرسانی کاربر
            conn.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, expiry, is_premium, last_active) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, new_expiry, 1 if license_type == 'premium' else 0, current_time))
            
            conn.commit()
            
            # لاگ فعالیت
            self.log_activity(user_id, "LICENSE_ACTIVATED", 
                            f"Activated {days}-day {license_type} license")
            
            expiry_date = datetime.fromtimestamp(new_expiry).strftime('%Y/%m/%d')
            return True, f"{message}\n📅 تاریخ انقضا: {expiry_date}"
    
    def delete_user(self, user_id: str) -> bool:
        """حذف کاربر از سیستم"""
        with self.get_connection() as conn:
            result = conn.execute(
                "DELETE FROM users WHERE user_id = ?", 
                (user_id,)
            )
            conn.commit()
            
            if result.rowcount > 0:
                self.log_activity("ADMIN", "USER_DELETED", f"Deleted user: {user_id}")
                logger.warning(f"🗑️ کاربر حذف شد: {user_id}")
                return True
            return False
    
    def get_all_users(self, limit: int = 100) -> List[sqlite3.Row]:
        """دریافت تمام کاربران"""
        with self.get_connection() as conn:
            return conn.execute('''
                SELECT user_id, username, first_name, expiry, role, 
                       strftime('%Y-%m-%d %H:%M', created_at) as created,
                       CASE 
                           WHEN expiry > ? THEN '✅ فعال'
                           ELSE '❌ منقضی'
                       END as status
                FROM users 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (time.time(), limit)).fetchall()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """دریافت آمار کامل سیستم"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # آمار کاربران
            cursor.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE expiry > ?", (time.time(),))
            stats['active_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
            stats['premium_users'] = cursor.fetchone()[0]
            
            # آمار لایسنس
            cursor.execute("SELECT COUNT(*) FROM licenses")
            stats['total_licenses'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM licenses WHERE is_active = 1")
            stats['active_licenses'] = cursor.fetchone()[0]
            
            # آمار سیگنال‌ها
            cursor.execute("SELECT COUNT(*) FROM signals")
            stats['total_signals'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM signals WHERE is_vip = 1")
            stats['vip_signals'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM signals WHERE result = 'win'")
            stats['winning_signals'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM signals WHERE result = 'loss'")
            stats['losing_signals'] = cursor.fetchone()[0]
            
            # محاسبه win rate
            if stats['total_signals'] > 0:
                stats['win_rate'] = round(
                    (stats['winning_signals'] / stats['total_signals']) * 100, 2
                )
            else:
                stats['win_rate'] = 0
            
            # آخرین فعالیت
            cursor.execute('''
                SELECT action, details, strftime('%Y-%m-%d %H:%M', timestamp) as time
                FROM activity_logs 
                ORDER BY timestamp DESC 
                LIMIT 5
            ''')
            stats['recent_activities'] = cursor.fetchall()
            
            return stats
    
    def save_signal(self, signal_data: Dict[str, Any]) -> str:
        """ذخیره سیگنال در دیتابیس"""
        signal_id = signal_data.get('signal_id', f"SIG-{uuid.uuid4().hex[:8].upper()}")
        
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO signals 
                (signal_id, symbol, entry_price, take_profit, stop_loss, 
                 win_probability, timestamp, generated_by, is_vip, 
                 risk_reward_ratio, signal_type, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_id,
                signal_data['symbol'],
                signal_data['current_price'],
                signal_data['take_profit'],
                signal_data['stop_loss'],
                signal_data['win_probability'],
                time.time(),
                signal_data.get('generated_by', 'BOT'),
                signal_data.get('is_vip', 0),
                signal_data.get('risk_reward_ratio', 0),
                signal_data.get('signal_type', 'regular'),
                signal_data.get('confidence', 'medium')
            ))
            conn.commit()
        
        self.log_activity(signal_data.get('generated_by', 'BOT'), 
                         "SIGNAL_GENERATED", 
                         f"Signal {signal_id} for {signal_data['symbol']}")
        
        logger.info(f"📈 سیگنال ذخیره شد: {signal_id} - {signal_data['symbol']}")
        return signal_id
    
    def backup_database(self) -> Optional[str]:
        """پشتیبان‌گیری از دیتابیس"""
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            
            backup_file = os.path.join(
                BACKUP_DIR, 
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            
            with self.get_connection() as source:
                with sqlite3.connect(backup_file) as destination:
                    source.backup(destination)
            
            self.log_activity("SYSTEM", "DATABASE_BACKUP", 
                            f"Backup created: {backup_file}")
            logger.info(f"💾 بکاپ ایجاد شد: {backup_file}")
            
            return backup_file
        except Exception as e:
            logger.error(f"❌ خطا در بکاپ گیری: {e}")
            return None

# ============================================
# 🧠 AI ANALYSIS ENGINE - موتور تحلیل هوش مصنوعی
# ============================================

class AIAnalysisEngine:
    """موتور تحلیل هوش مصنوعی پیشرفته"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 دقیقه کش
        logger.info("🧠 م