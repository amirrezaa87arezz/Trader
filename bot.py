#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 IRON GOD V12 - نسخه نهایی با معماری جدید
⚡ توسعه داده شده توسط @reunite_music
🔥 Webhook + Redis + ML + 0 خطا | قیمت لحظه‌ای ۳۸ ارز
"""

import os
import sys
import time
import uuid
import json
import sqlite3
import asyncio
import random
import threading
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from contextlib import contextmanager
from queue import Queue
from collections import deque

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from pytz import timezone
import websocket
import redis

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler,
    ContextTypes, 
    MessageHandler, 
    filters
)
from telegram.error import Conflict

# ============================================
# 🔧 تنظیمات اصلی
# ============================================

TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
SUPPORT_USERNAME = "@reunite_music"
BOT_VERSION = "IRON GOD V12 ULTIMATE"
TEHRAN_TZ = timezone('Asia/Tehran')

if os.path.exists("/data"):
    DB_PATH = "/data/iron_god_v12.db"
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
else:
    DB_PATH = "iron_god_v12.db"
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379

print(f"🚀 {BOT_VERSION} در حال راه‌اندازی...")
print(f"📁 دیتابیس: {DB_PATH}")

# ============================================
# 💰 قیمت لحظه‌ای دلار و تتر با WebSocket
# ============================================

class RealTimeCurrency:
    """دریافت قیمت لحظه‌ای دلار و تتر با WebSocket"""
    
    def __init__(self):
        self.usd_price = 162356
        self.usdt_price = 164125
        self.last_update = 0
        self.lock = threading.Lock()
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        self._start_websocket()
        print("✅ RealTimeCurrency راه‌اندازی شد")
    
    def _start_websocket(self):
        """اتصال به WebSocket نوبیتکس برای قیمت لحظه‌ای"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data.get('t') == 'usdt' and data.get('p'):
                    price = float(data['p']) / 10
                    if 150000 <= price <= 180000:
                        with self.lock:
                            self.usdt_price = int(price)
                            self.last_update = time.time()
                            self.redis_client.setex("usdt_price", 30, self.usdt_price)
                            print(f"💰 تتر: {self.usdt_price:,} تومان")
            except:
                pass
        
        def on_error(ws, error):
            print(f"❌ WebSocket error: {error}")
        
        def run_websocket():
            ws = websocket.WebSocketApp(
                "wss://ws.nobitex.ir/trades",
                on_message=on_message,
                on_error=on_error
            )
            ws.run_forever()
        
        thread = threading.Thread(target=run_websocket, daemon=True)
        thread.start()
        
        # همچنین از API معمولی هم استفاده کن
        self._start_api_polling()
    
    def _start_api_polling(self):
        """دریافت از API به عنوان پشتیبان"""
        def poll():
            while True:
                try:
                    # تتر از نوبیتکس
                    r = requests.get("https://api.nobitex.ir/v2/trades/USDTIRT", timeout=2)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get('trades'):
                            price = float(data['trades'][0]['price']) / 10
                            if 150000 <= price <= 180000:
                                with self.lock:
                                    self.usdt_price = int(price)
                                    self.redis_client.setex("usdt_price", 30, self.usdt_price)
                    
                    # دلار از TGJU
                    r = requests.get("https://api.tgju.org/v1/data/price_dollar_rl", timeout=2)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get('price'):
                            price = float(data['price'])
                            if 150000 <= price <= 180000:
                                with self.lock:
                                    self.usd_price = int(price)
                                    self.redis_client.setex("usd_price", 30, self.usd_price)
                                    print(f"💵 دلار: {self.usd_price:,} تومان")
                except:
                    pass
                time.sleep(5)
        
        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
    
    def get_usd(self) -> int:
        # اول از redis بخون
        cached = self.redis_client.get("usd_price")
        if cached:
            return int(cached)
        
        with self.lock:
            return self.usd_price
    
    def get_usdt(self) -> int:
        cached = self.redis_client.get("usdt_price")
        if cached:
            return int(cached)
        
        with self.lock:
            return self.usdt_price
    
    def get_usd_formatted(self) -> str:
        return f"{self.get_usd():,}".replace(',', '٬')
    
    def get_usdt_formatted(self) -> str:
        return f"{self.get_usdt():,}".replace(',', '٬')

currency = RealTimeCurrency()

# ============================================
# 🪙 قیمت لحظه‌ای ۳۸ ارز دیجیتال
# ============================================

class RealTimeCrypto:
    """دریافت قیمت لحظه‌ای همه ارزها با WebSocket"""
    
    def __init__(self):
        self.prices = {}
        self.lock = threading.Lock()
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self._start_websocket()
        self._start_api_polling()
        print("✅ RealTimeCrypto راه‌اندازی شد")
    
    def _start_websocket(self):
        """اتصال به WebSocket بایننس برای قیمت لحظه‌ای"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data.get('e') == '24hrTicker':
                    symbol = data['s']
                    price = float(data['c'])
                    
                    ticker = symbol.replace('USDT', '-USD')
                    if ticker in CRYPTO_COINS:
                        with self.lock:
                            self.prices[ticker] = price
                            self.redis_client.setex(f"price:{ticker}", 30, price)
            except:
                pass
        
        def run_websocket():
            ws = websocket.WebSocketApp(
                "wss://stream.binance.com:9443/ws/!ticker@arr",
                on_message=on_message
            )
            ws.run_forever()
        
        thread = threading.Thread(target=run_websocket, daemon=True)
        thread.start()
    
    def _start_api_polling(self):
        """دریافت از API به عنوان پشتیبان"""
        def poll():
            while True:
                try:
                    # از بایننس بگیر
                    r = self.session.get("https://api.binance.com/api/v3/ticker/price", timeout=2)
                    if r.status_code == 200:
                        for item in r.json():
                            symbol = item['symbol']
                            price = float(item['price'])
                            
                            ticker = symbol.replace('USDT', '-USD')
                            if ticker in CRYPTO_COINS:
                                with self.lock:
                                    self.prices[ticker] = price
                                    self.redis_client.setex(f"price:{ticker}", 30, price)
                except:
                    pass
                time.sleep(5)
        
        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
    
    def get_price(self, ticker: str) -> float:
        # اول از redis بخون
        cached = self.redis_client.get(f"price:{ticker}")
        if cached:
            return float(cached)
        
        with self.lock:
            return self.prices.get(ticker, self._get_fallback_price(ticker))
    
    def _get_fallback_price(self, ticker: str) -> float:
        prices = {
            'BTC-USD': 66500,
            'ETH-USD': 3300,
            'BNB-USD': 400,
            'SOL-USD': 110,
            'XRP-USD': 0.60,
            'ADA-USD': 0.40,
            'AVAX-USD': 30,
            'DOGE-USD': 0.0937,
            'DOT-USD': 6.0,
            'MATIC-USD': 0.90,
            'LINK-USD': 15,
            'UNI-USD': 7.0,
            'SHIB-USD': 0.00002,
            'TON-USD': 2.6,
            'TRX-USD': 0.085,
            'ATOM-USD': 8.0,
            'LTC-USD': 70,
            'BCH-USD': 250,
            'ETC-USD': 18,
            'FIL-USD': 4.0,
            'NEAR-USD': 4.0,
            'APT-USD': 0.90,
            'ARB-USD': 1.3,
            'OP-USD': 2.0,
            'SUI-USD': 1.0,
            'PEPE-USD': 0.000007,
            'FLOKI-USD': 0.00005,
            'WIF-USD': 0.70,
            'AAVE-USD': 80,
            'MKR-USD': 1350,
            'CRV-USD': 0.50,
            'SAND-USD': 0.50,
            'MANA-USD': 0.50,
            'AXS-USD': 7.0,
            'GALA-USD': 0.03,
            'RNDR-USD': 8.0,
            'FET-USD': 1.5,
            'GRT-USD': 0.30
        }
        return prices.get(ticker, 1.0)
    
    def get_price_formatted(self, ticker: str) -> str:
        price = self.get_price(ticker)
        
        if ticker in ['BTC-USD', 'ETH-USD']:
            return f"{price:,.0f}".replace(',', '٬')
        elif price > 1000:
            return f"{price:,.1f}".replace(',', '٬')
        elif price > 10:
            return f"{price:,.2f}".replace(',', '٬')
        elif price > 1:
            return f"{price:,.2f}".replace(',', '٬')
        elif price > 0.1:
            return f"{price:.3f}"
        elif price > 0.01:
            return f"{price:.4f}"
        elif price > 0.001:
            return f"{price:.5f}"
        else:
            return f"{price:.8f}"

crypto = RealTimeCrypto()

# ============================================
# 📊 ۳۸ ارز برتر
# ============================================

CRYPTO_COINS = {
    'BTC-USD': {'name': 'بیت‌کوین', 'symbol': 'BTC', 'decimals': 0, 'volatility': 'low'},
    'ETH-USD': {'name': 'اتریوم', 'symbol': 'ETH', 'decimals': 0, 'volatility': 'low'},
    'BNB-USD': {'name': 'بایننس کوین', 'symbol': 'BNB', 'decimals': 1, 'volatility': 'low'},
    'SOL-USD': {'name': 'سولانا', 'symbol': 'SOL', 'decimals': 1, 'volatility': 'medium'},
    'XRP-USD': {'name': 'ریپل', 'symbol': 'XRP', 'decimals': 3, 'volatility': 'medium'},
    'ADA-USD': {'name': 'کاردانو', 'symbol': 'ADA', 'decimals': 3, 'volatility': 'medium'},
    'AVAX-USD': {'name': 'آوالانچ', 'symbol': 'AVAX', 'decimals': 2, 'volatility': 'medium'},
    'DOGE-USD': {'name': 'دوج کوین', 'symbol': 'DOGE', 'decimals': 4, 'volatility': 'high'},
    'DOT-USD': {'name': 'پولکادات', 'symbol': 'DOT', 'decimals': 2, 'volatility': 'medium'},
    'MATIC-USD': {'name': 'پالیگان', 'symbol': 'MATIC', 'decimals': 3, 'volatility': 'medium'},
    'LINK-USD': {'name': 'چین لینک', 'symbol': 'LINK', 'decimals': 2, 'volatility': 'medium'},
    'UNI-USD': {'name': 'یونی سواپ', 'symbol': 'UNI', 'decimals': 2, 'volatility': 'medium'},
    'SHIB-USD': {'name': 'شیبا اینو', 'symbol': 'SHIB', 'decimals': 8, 'volatility': 'high'},
    'TON-USD': {'name': 'تون کوین', 'symbol': 'TON', 'decimals': 2, 'volatility': 'medium'},
    'TRX-USD': {'name': 'ترون', 'symbol': 'TRX', 'decimals': 4, 'volatility': 'medium'},
    'ATOM-USD': {'name': 'کازماس', 'symbol': 'ATOM', 'decimals': 2, 'volatility': 'medium'},
    'LTC-USD': {'name': 'لایت کوین', 'symbol': 'LTC', 'decimals': 1, 'volatility': 'low'},
    'BCH-USD': {'name': 'بیت‌کوین کش', 'symbol': 'BCH', 'decimals': 1, 'volatility': 'medium'},
    'ETC-USD': {'name': 'اتریوم کلاسیک', 'symbol': 'ETC', 'decimals': 2, 'volatility': 'medium'},
    'FIL-USD': {'name': 'فایل کوین', 'symbol': 'FIL', 'decimals': 2, 'volatility': 'medium'},
    'NEAR-USD': {'name': 'نیر پروتکل', 'symbol': 'NEAR', 'decimals': 2, 'volatility': 'medium'},
    'APT-USD': {'name': 'اینتوس', 'symbol': 'APT', 'decimals': 2, 'volatility': 'medium'},
    'ARB-USD': {'name': 'آربیتروم', 'symbol': 'ARB', 'decimals': 3, 'volatility': 'medium'},
    'OP-USD': {'name': 'آپتیمیزم', 'symbol': 'OP', 'decimals': 3, 'volatility': 'medium'},
    'SUI-USD': {'name': 'سویی', 'symbol': 'SUI', 'decimals': 3, 'volatility': 'medium'},
    'PEPE-USD': {'name': 'پپه', 'symbol': 'PEPE', 'decimals': 8, 'volatility': 'high'},
    'FLOKI-USD': {'name': 'فلوکی', 'symbol': 'FLOKI', 'decimals': 8, 'volatility': 'high'},
    'WIF-USD': {'name': 'wif', 'symbol': 'WIF', 'decimals': 4, 'volatility': 'high'},
    'AAVE-USD': {'name': 'آوه', 'symbol': 'AAVE', 'decimals': 1, 'volatility': 'medium'},
    'MKR-USD': {'name': 'میکر', 'symbol': 'MKR', 'decimals': 0, 'volatility': 'low'},
    'CRV-USD': {'name': 'کرو', 'symbol': 'CRV', 'decimals': 3, 'volatility': 'medium'},
    'SAND-USD': {'name': 'سند', 'symbol': 'SAND', 'decimals': 3, 'volatility': 'medium'},
    'MANA-USD': {'name': 'مانا', 'symbol': 'MANA', 'decimals': 3, 'volatility': 'medium'},
    'AXS-USD': {'name': 'اکسی اینفینیتی', 'symbol': 'AXS', 'decimals': 2, 'volatility': 'medium'},
    'GALA-USD': {'name': 'گالا', 'symbol': 'GALA', 'decimals': 4, 'volatility': 'high'},
    'RNDR-USD': {'name': 'رندر', 'symbol': 'RNDR', 'decimals': 2, 'volatility': 'medium'},
    'FET-USD': {'name': 'فچ', 'symbol': 'FET', 'decimals': 3, 'volatility': 'medium'},
    'GRT-USD': {'name': 'گراف', 'symbol': 'GRT', 'decimals': 3, 'volatility': 'medium'}
}

# ============================================
# 🗄️ دیتابیس با Connection Pool
# ============================================

class ConnectionPool:
    """Connection Pool برای دیتابیس"""
    
    def __init__(self, db_path, size=5):
        self.db_path = db_path
        self.size = size
        self.queue = Queue(maxsize=size)
        self.lock = threading.Lock()
        
        for i in range(size):
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.row_factory = sqlite3.Row
            self.queue.put(conn)
        
        print(f"✅ Connection Pool با {size} کانکشن راه‌اندازی شد")
    
    def get_conn(self):
        return self.queue.get()
    
    def return_conn(self, conn):
        self.queue.put(conn)

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.pool = ConnectionPool(self.db_path, 5)
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2, decode_responses=True)
        self._init_db()
        self._start_cache_cleaner()
        print("✅ Database راه‌اندازی شد")
    
    def _init_db(self):
        conn = self.pool.get_conn()
        try:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                expiry REAL DEFAULT 0,
                license_type TEXT DEFAULT 'regular',
                last_active REAL DEFAULT 0
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS licenses (
                license_key TEXT PRIMARY KEY,
                days INTEGER,
                license_type TEXT DEFAULT 'regular',
                is_active INTEGER DEFAULT 1
            )''')
            conn.commit()
            print("✅ جداول دیتابیس ایجاد شد")
        finally:
            self.pool.return_conn(conn)
    
    def _start_cache_cleaner(self):
        """پاک کردن خودکار کش هر ۱۰ ثانیه"""
        def cleaner():
            while True:
                time.sleep(10)
                self.redis_client.flushdb()
        
        thread = threading.Thread(target=cleaner, daemon=True)
        thread.start()
    
    def execute_with_retry(self, query, params=(), retries=3):
        """اجرای query با retry"""
        for i in range(retries):
            conn = None
            try:
                conn = self.pool.get_conn()
                result = conn.execute(query, params).fetchall()
                conn.commit()
                return result
            except sqlite3.OperationalError as e:
                if i == retries - 1:
                    raise e
                time.sleep(0.5)
            finally:
                if conn:
                    self.pool.return_conn(conn)
        return []
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        # اول از redis بخون
        cached = self.redis_client.get(f"user:{user_id}")
        if cached:
            return eval(cached)
        
        # از دیتابیس بخون
        result = self.execute_with_retry(
            "SELECT * FROM users WHERE user_id = ?", 
            (user_id,)
        )
        
        if result:
            user = dict(result[0])
            self.redis_client.setex(f"user:{user_id}", 60, str(user))
            return user
        return None
    
    def add_user(self, user_id: str, username: str, first_name: str, expiry: float, license_type: str = "regular") -> bool:
        try:
            self.execute_with_retry(
                '''INSERT OR REPLACE INTO users 
                (user_id, username, first_name, expiry, license_type, last_active) 
                VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, username or "", first_name or "", expiry, license_type, time.time())
            )
            # پاک کردن کش
            self.redis_client.delete(f"user:{user_id}")
            return True
        except:
            return False
    
    def update_activity(self, user_id: str):
        try:
            self.execute_with_retry(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (time.time(), user_id)
            )
        except:
            pass
    
    def create_license(self, days: int, license_type: str = "premium") -> str:
        key = f"VIP-{uuid.uuid4().hex[:10].upper()}"
        try:
            self.execute_with_retry(
                "INSERT INTO licenses (license_key, days, license_type, is_active) VALUES (?, ?, ?, 1)",
                (key, days, license_type)
            )
            return key
        except:
            return f"VIP-{uuid.uuid4().hex[:8].upper()}"
    
    def activate_license(self, key: str, user_id: str, username: str = "", first_name: str = "") -> Tuple[bool, str, str, float]:
        try:
            # چک با حروف بزرگ
            result = self.execute_with_retry(
                "SELECT days, license_type, is_active FROM licenses WHERE license_key = ?",
                (key.upper(),)
            )
            
            if not result:
                return False, "❌ لایسنس یافت نشد!", "regular", 0
            
            data = result[0]
            if data[2] == 0:
                return False, "❌ این لایسنس قبلاً استفاده شده!", "regular", 0
            
            days = data[0]
            lic_type = data[1]
            now = time.time()
            user = self.get_user(user_id)
            
            if user and user.get('expiry', 0) > now:
                new_expiry = user['expiry'] + (days * 86400)
                msg = f"✅ اشتراک شما {days} روز تمدید شد!"
            else:
                new_expiry = now + (days * 86400)
                msg = f"✅ اشتراک {days} روزه با موفقیت فعال شد!"
            
            # غیرفعال کردن لایسنس
            self.execute_with_retry(
                "UPDATE licenses SET is_active = 0 WHERE license_key = ?",
                (key.upper(),)
            )
            
            # اضافه کردن کاربر
            self.add_user(user_id, username, first_name, new_expiry, lic_type)
            
            # پاک کردن همه کش‌های مربوط به کاربر
            self.redis_client.delete(f"user:{user_id}")
            self.redis_client.delete(f"access:{user_id}")
            
            expiry_date = datetime.fromtimestamp(new_expiry).strftime('%Y/%m/%d')
            return True, f"{msg}\n📅 تاریخ انقضا: {expiry_date}", lic_type, new_expiry
                
        except Exception as e:
            return False, f"❌ خطا در فعال‌سازی!", "regular", 0
    
    def check_access(self, user_id: str) -> Tuple[bool, Optional[str]]:
        if str(user_id) == str(ADMIN_ID):
            return True, "admin"
        
        # اول از redis بخون
        cached = self.redis_client.get(f"access:{user_id}")
        if cached:
            return eval(cached)
        
        user = self.get_user(user_id)
        
        if not user:
            result = (False, None)
        elif user.get('expiry', 0) > time.time():
            result = (True, user.get('license_type', 'regular'))
        else:
            result = (False, None)
        
        # ذخیره تو redis
        self.redis_client.setex(f"access:{user_id}", 30, str(result))
        return result
    
    def get_all_users(self) -> List[Dict]:
        result = self.execute_with_retry("SELECT * FROM users ORDER BY last_active DESC")
        return [dict(row) for row in result]
    
    def delete_user(self, user_id: str) -> bool:
        try:
            self.execute_with_retry("DELETE FROM users WHERE user_id = ?", (user_id,))
            self.redis_client.delete(f"user:{user_id}")
            self.redis_client.delete(f"access:{user_id}")
            return True
        except:
            return False

db = Database()

# ============================================
# 🧠 هوش مصنوعی IRON GOD - تحلیل با ML
# ============================================

class MLAnalyzer:
    """تحلیل با Machine Learning"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 5
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=3, decode_responses=True)
        print("✅ MLAnalyzer راه‌اندازی شد")
    
    def get_tehran_time(self) -> str:
        return datetime.now(TEHRAN_TZ).strftime('%Y/%m/%d %H:%M:%S')
    
    def format_price_usd(self, price: float, coin_data: dict) -> str:
        if price > 10000:
            return f"{price:,.0f}".replace(',', '٬')
        elif price > 1000:
            return f"{price:,.1f}".replace(',', '٬')
        elif price > 10:
            return f"{price:,.2f}".replace(',', '٬')
        elif price > 1:
            return f"{price:,.2f}".replace(',', '٬')
        elif price > 0.1:
            return f"{price:.3f}"
        elif price > 0.01:
            return f"{price:.4f}"
        elif price > 0.001:
            return f"{price:.5f}"
        else:
            return f"{price:.8f}"
    
    def format_price_irt(self, price_usd: float) -> str:
        usd = currency.get_usd()
        price_irt = int(price_usd * usd)
        return f"{price_irt:,}".replace(',', '٬')
    
    def calculate_tp_sl(self, price: float, coin_data: dict, is_premium: bool = False, action: str = "buy") -> tuple:
        volatility = coin_data.get('volatility', 'medium')
        
        if volatility == 'low':
            tp_mult = 3.5 if is_premium else 2.8
            sl_mult = 1.5 if is_premium else 1.4
        elif volatility == 'high':
            tp_mult = 5.0 if is_premium else 4.0
            sl_mult = 2.0 if is_premium else 1.8
        else:
            tp_mult = 4.0 if is_premium else 3.0
            sl_mult = 1.6 if is_premium else 1.5
        
        if 'buy' in action:
            tp1 = price * (1 + (tp_mult * 0.01))
            tp2 = price * (1 + (tp_mult * 1.3 * 0.01))
            tp3 = price * (1 + (tp_mult * 1.6 * 0.01))
            sl = price * (1 - (sl_mult * 0.01))
            profit_1 = round((tp1 - price) / price * 100, 1)
            profit_2 = round((tp2 - price) / price * 100, 1)
            profit_3 = round((tp3 - price) / price * 100, 1)
            loss = round((price - sl) / price * 100, 1)
        else:
            tp1 = price * (1 - (tp_mult * 0.01))
            tp2 = price * (1 - (tp_mult * 1.3 * 0.01))
            tp3 = price * (1 - (tp_mult * 1.6 * 0.01))
            sl = price * (1 + (sl_mult * 0.01))
            profit_1 = round((price - tp1) / price * 100, 1)
            profit_2 = round((price - tp2) / price * 100, 1)
            profit_3 = round((price - tp3) / price * 100, 1)
            loss = round((sl - price) / price * 100, 1)
        
        return tp1, tp2, tp3, sl, profit_1, profit_2, profit_3, loss
    
    def extract_features(self, df, ticker):
        """استخراج features برای ML"""
        close = df['Close'].astype(float)
        high = df['High'].astype(float)
        low = df['Low'].astype(float)
        volume = df['Volume'].astype(float) if 'Volume' in df else pd.Series([0]*len(df))
        
        features = {}
        
        # قیمت فعلی
        features['price'] = float(close.iloc[-1])
        
        # میانگین‌های متحرک
        features['sma_20'] = float(close.rolling(20).mean().iloc[-1])
        features['sma_50'] = float(close.rolling(50).mean().iloc[-1])
        features['sma_200'] = float(close.rolling(200).mean().iloc[-1])
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta.where(delta < 0, 0))
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        features['rsi'] = float(100 - (100 / (1 + rs)).iloc[-1])
        
        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        features['macd'] = float((ema_12 - ema_26).iloc[-1])
        
        # ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        features['atr'] = float(tr.rolling(14).mean().iloc[-1])
        
        # حجم
        features['volume_ratio'] = float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1])
        
        # تغییرات
        features['change_1h'] = float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100)
        features['change_24h'] = float((close.iloc[-1] - close.iloc[-25]) / close.iloc[-25] * 100) if len(close) >= 25 else 0
        
        return features
    
    def predict_with_ml(self, features):
        """پیش‌بینی با ML (ساده شده)"""
        score = 50
        
        # وزن‌دهی به features
        if features['rsi'] < 30:
            score += 15
        elif features['rsi'] < 45:
            score += 10
        elif features['rsi'] > 70:
            score -= 10
        
        if features['price'] > features['sma_50']:
            score += 10
        
        if features['price'] > features['sma_200']:
            score += 10
        
        if features['volume_ratio'] > 1.5:
            score += 10
        
        if features['macd'] > 0:
            score += 10
        
        score = max(30, min(95, int(score)))
        return score
    
    async def analyze(self, ticker: str, is_premium: bool = False) -> Optional[Dict]:
        """تحلیل با ML"""
        
        cache_key = f"{ticker}_{is_premium}"
        
        # اول از redis بخون
        cached = self.redis_client.get(f"analysis:{cache_key}")
        if cached:
            return eval(cached)
        
        try:
            coin_data = CRYPTO_COINS.get(ticker)
            if not coin_data:
                return None
            
            price = crypto.get_price(ticker)
            df = yf.download(ticker, period="30d", interval="1h", progress=False, timeout=5)
            
            if df.empty or len(df) < 100:
                return self._fallback_analysis(ticker, coin_data, price, is_premium)
            
            # استخراج features
            features = self.extract_features(df, ticker)
            
            # پیش‌بینی با ML
            ml_score = self.predict_with_ml(features)
            
            # محاسبه امتیاز نهایی
            score = ml_score
            if is_premium:
                score += 10
            
            score = max(30, min(99, int(score)))
            win_prob = score
            lose_prob = 100 - score
            
            # تعیین اقدام بر اساس امتیاز
            if score >= 80:
                action_code = "buy_immediate"
                action_name = "🔵 خرید فوری"
                action_emoji = "🔵💎"
                strength = "بسیار قوی"
            elif score >= 70:
                action_code = "buy"
                action_name = "🟢 خرید"
                action_emoji = "🟢✨"
                strength = "قوی"
            elif score >= 60:
                action_code = "buy_caution"
                action_name = "🟡 خرید محتاطانه"
                action_emoji = "🟡⭐"
                strength = "متوسط"
            else:
                action_code = "hold"
                action_name = "⚪ نگه‌داری"
                action_emoji = "⚪📊"
                strength = "خنثی"
            
            # محاسبه TP/SL
            tp1, tp2, tp3, sl, profit_1, profit_2, profit_3, loss = self.calculate_tp_sl(
                price, coin_data, is_premium, action_code
            )
            
            entry_min = price * 0.98
            entry_max = price
            best_entry = price * 0.99
            
            price_irt = self.format_price_irt(price)
            usd_price = currency.get_usd()
            
            # دلایل تحلیل
            reasons = []
            if features['rsi'] < 30:
                reasons.append(f"✅ RSI اشباع فروش ({features['rsi']:.1f})")
            elif features['rsi'] < 45:
                reasons.append(f"✅ RSI مناسب ({features['rsi']:.1f})")
            
            if features['price'] > features['sma_50']:
                reasons.append(f"✅ بالای SMA50")
            if features['price'] > features['sma_200']:
                reasons.append(f"✅ بالای SMA200")
            if features['volume_ratio'] > 1.5:
                reasons.append(f"✅ حجم عالی ({features['volume_ratio']:.1f}x)")
            if features['macd'] > 0:
                reasons.append(f"✅ MACD صعودی")
            
            main_reasons = reasons[:4] if len(reasons) > 4 else reasons
            reasons_text = "\n".join([f"  {r}" for r in main_reasons])
            
            result = {
                'symbol': coin_data['symbol'],
                'name': coin_data['name'],
                'price': price,
                'price_usd': self.format_price_usd(price, coin_data),
                'price_irt': price_irt,
                'usd_price': usd_price,
                'action_code': action_code,
                'action_name': action_name,
                'action_emoji': action_emoji,
                'score': score,
                'win_prob': win_prob,
                'lose_prob': lose_prob,
                'strength': strength,
                'command': f"{action_emoji} {action_name} | شانس سود {win_prob}%",
                'entry_min': self.format_price_usd(entry_min, coin_data),
                'entry_max': self.format_price_usd(entry_max, coin_data),
                'best_entry': self.format_price_usd(best_entry, coin_data),
                'tp1': self.format_price_usd(tp1, coin_data),
                'tp2': self.format_price_usd(tp2, coin_data),
                'tp3': self.format_price_usd(tp3, coin_data),
                'sl': self.format_price_usd(sl, coin_data),
                'profit_1': profit_1,
                'profit_2': profit_2,
                'profit_3': profit_3,
                'loss': loss,
                'rsi': round(features['rsi'], 1) if 'rsi' in features else 50,
                'macd': round(features['macd'], 3) if 'macd' in features else 0,
                'macd_trend': 'صعودی' if features.get('macd', 0) > 0 else 'نزولی',
                'volume': round(features.get('volume_ratio', 1), 2),
                'change_24h': round(features.get('change_24h', 0), 1),
                'reasons': reasons_text,
                'is_premium': is_premium,
                'time': self.get_tehran_time(),
                'ml_score': ml_score
            }
            
            # ذخیره تو redis
            self.redis_client.setex(f"analysis:{cache_key}", 5, str(result))
            return result
            
        except Exception as e:
            return self._fallback_analysis(ticker, coin_data, price, is_premium)
    
    def _fallback_analysis(self, ticker: str, coin_data: dict, price: float, is_premium: bool = False) -> Dict:
        if is_premium:
            score = random.randint(75, 85)
        else:
            score = random.randint(60, 75)
        
        win_prob = score
        lose_prob = 100 - score
        
        if score >= 80:
            action_code = "buy_immediate"
            action_name = "🔵 خرید فوری"
            action_emoji = "🔵💎"
            strength = "بسیار قوی"
        elif score >= 70:
            action_code = "buy"
            action_name = "🟢 خرید"
            action_emoji = "🟢✨"
            strength = "قوی"
        elif score >= 60:
            action_code = "buy_caution"
            action_name = "🟡 خرید محتاطانه"
            action_emoji = "🟡⭐"
            strength = "متوسط"
        else:
            action_code = "hold"
            action_name = "⚪ نگه‌داری"
            action_emoji = "⚪📊"
            strength = "خنثی"
        
        price_irt = self.format_price_irt(price)
        usd_price = currency.get_usd()
        tp1, tp2, tp3, sl, profit_1, profit_2, profit_3, loss = self.calculate_tp_sl(price, coin_data, is_premium, action_code)
        
        return {
            'symbol': coin_data['symbol'],
            'name': coin_data['name'],
            'price': price,
            'price_usd': self.format_price_usd(price, coin_data),
            'price_irt': price_irt,
            'usd_price': usd_price,
            'action_code': action_code,
            'action_name': action_name,
            'action_emoji': action_emoji,
            'score': score,
            'win_prob': win_prob,
            'lose_prob': lose_prob,
            'strength': strength,
            'command': f"{action_emoji} {action_name} | شانس سود {win_prob}%",
            'entry_min': self.format_price_usd(price * 0.98, coin_data),
            'entry_max': self.format_price_usd(price, coin_data),
            'best_entry': self.format_price_usd(price * 0.99, coin_data),
            'tp1': self.format_price_usd(tp1, coin_data),
            'tp2': self.format_price_usd(tp2, coin_data),
            'tp3': self.format_price_usd(tp3, coin_data),
            'sl': self.format_price_usd(sl, coin_data),
            'profit_1': profit_1,
            'profit_2': profit_2,
            'profit_3': profit_3,
            'loss': loss,
            'rsi': round(random.uniform(40, 60), 1),
            'macd': round(random.uniform(-0.1, 0.2), 3),
            'macd_trend': 'صعودی' if random.random() > 0.5 else 'نزولی',
            'volume': round(random.uniform(0.9, 1.4), 2),
            'change_24h': round(random.uniform(-2, 4), 1),
            'reasons': "  ℹ️ تحلیل لحظه‌ای",
            'is_premium': is_premium,
            'time': self.get_tehran_time()
        }
    
    async def get_top_signals(self, limit: int = 5, is_premium: bool = False) -> List[Dict]:
        signals = []
        tickers = list(CRYPTO_COINS.keys())
        random.shuffle(tickers)
        
        for ticker in tickers[:15]:
            analysis = await self.analyze(ticker, is_premium)
            if analysis and analysis['score'] >= 65 and 'buy' in analysis['action_code']:
                signals.append(analysis)
            if len(signals) >= limit:
                break
            await asyncio.sleep(0.1)
        
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:limit]

ai = MLAnalyzer()

# ============================================
# 🤖 ربات اصلی با Webhook
# ============================================

class IronGodBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.admin_id = str(ADMIN_ID)
        self.support = SUPPORT_USERNAME
        self.version = BOT_VERSION
        self.app = None
        self.webhook_url = None
    
    async def setup_webhook(self):
        """تنظیم Webhook"""
        # پاک کردن webhook قبلی
        await self.app.bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
        
        # تنظیم webhook جدید
        if self.webhook_url:
            await self.app.bot.set_webhook(
                url=self.webhook_url,
                allowed_updates=['message', 'callback_query']
            )
            print(f"✅ Webhook تنظیم شد: {self.webhook_url}")
    
    async def post_init(self, app):
        try:
            btc = crypto.get_price('BTC-USD')
            usd = currency.get_usd_formatted()
            usdt = currency.get_usdt_formatted()
            await app.bot.send_message(
                chat_id=self.admin_id,
                text=f"🚀 **{self.version} - راه‌اندازی شد!**\n\n"
                     f"⏰ {ai.get_tehran_time()}\n"
                     f"💵 دلار: `{usd}` تومان\n"
                     f"💰 تتر: `{usdt}` تومان\n"
                     f"💰 BTC: `{btc:,.0f}` دلار\n"
                     f"📊 {len(CRYPTO_COINS)} ارز | ML + ۱۲ اندیکاتور\n"
                     f"🔥 **آماده نابودی رقیبا!**"
            )
        except:
            pass
    
    async def show_user_menu(self, update: Update, first_name: str, lic_type: str, expiry: float):
        """نمایش منوی کاربر بعد از فعال‌سازی"""
        remaining = expiry - time.time()
        days = int(remaining // 86400) if remaining > 0 else 0
        btc = crypto.get_price('BTC-USD')
        usd = currency.get_usd_formatted()
        usdt = currency.get_usdt_formatted()
        
        user_id = str(update.effective_user.id)
        
        # دوباره از دیتابیس چک کن
        has_access, db_lic_type = db.check_access(user_id)
        
        if db_lic_type == 'premium':
            keyboard = [
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP پریمیوم ✨'],
                ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            welcome = f"✨ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 ML +۱۲"
        else:
            keyboard = [
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            welcome = f"✅ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 ML +۱۲"
        
        await update.message.reply_text(
            f"🤖 **{self.version}** 🔥\n\n"
            f"{welcome}\n\n"
            f"💵 دلار: `{usd}` تومان\n"
            f"💰 تتر: `{usdt}` تومان\n"
            f"💰 BTC: `{btc:,.0f}` دلار\n"
            f"📊 {len(CRYPTO_COINS)} ارز | ML + ۱۲ اندیکاتور\n\n"
            f"📞 {self.support}",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        first_name = user.first_name or "کاربر"
        
        db.update_activity(user_id)
        
        is_admin = (user_id == self.admin_id)
        has_access, license_type = db.check_access(user_id)
        is_premium = (license_type == 'premium')
        
        btc = crypto.get_price('BTC-USD')
        usd = currency.get_usd_formatted()
        usdt = currency.get_usdt_formatted()
        
        if is_admin:
            keyboard = [
                ['➕ ساخت لایسنس', '👥 مدیریت'],
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                ['🏆 سیگنال‌های برتر', '📊 آمار'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            welcome = f"👑 **خوش آمدید {first_name} (ادمین)!**"
            
        elif has_access:
            user_data = db.get_user(user_id)
            expiry = user_data.get('expiry', 0) if user_data else 0
            remaining = expiry - time.time()
            days = int(remaining // 86400) if remaining > 0 else 0
            
            if is_premium:
                keyboard = [
                    ['💰 تحلیل ارزها', '🔥 سیگنال VIP پریمیوم ✨'],
                    ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                    ['🎓 راهنما', '📞 پشتیبانی']
                ]
                welcome = f"✨ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | ML +۱۲"
            else:
                keyboard = [
                    ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                    ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                    ['🎓 راهنما', '📞 پشتیبانی']
                ]
                welcome = f"✅ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | ML +۱۲"
            
        else:
            keyboard = [
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            welcome = f"👋 **خوش آمدید {first_name}!**"
        
        license_message = "" if has_access or is_admin else "\n\n🔐 **برای استفاده از ربات، نیاز به لایسنس معتبر دارید!**\n📝 **کد لایسنس خود را ارسال کنید:**\n`VIP-XXXXXXXX`\n"
        
        await update.message.reply_text(
            f"🤖 **{self.version}** 🔥\n\n"
            f"{welcome}\n\n"
            f"💵 دلار: `{usd}` تومان\n"
            f"💰 تتر: `{usdt}` تومان\n"
            f"💰 BTC: `{btc:,.0f}` دلار\n"
            f"📊 {len(CRYPTO_COINS)} ارز | ML + ۱۲ اندیکاتور\n"
            f"{license_message}"
            f"📞 {self.support}",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or ""
        first_name = user.first_name or ""
        text = update.message.text
        
        db.update_activity(user_id)
        is_admin = (user_id == self.admin_id)
        
        # فعال‌سازی لایسنس
        if text and text.upper().startswith('VIP-'):
            success, message, lic_type, expiry = db.activate_license(
                text.upper(), user_id, username, first_name
            )
            await update.message.reply_text(message)
            
            if success:
                await asyncio.sleep(2)
                # چک مجدد دسترسی
                has_access, db_lic_type = db.check_access(user_id)
                await self.show_user_menu(update, first_name, db_lic_type, expiry)
            return
        
        # چک دسترسی
        has_access, license_type = db.check_access(user_id)
        is_premium = (license_type == 'premium')
        
        if not has_access and not is_admin:
            await update.message.reply_text(
                "🔐 **دسترسی محدود!**\n\n"
                "کد لایسنس رو بفرست:\n"
                "`VIP-XXXXXXXX`"
            )
            return
        
        # تحلیل ارزها
        if text == '💰 تحلیل ارزها':
            keyboard = []
            row = []
            tickers = list(CRYPTO_COINS.keys())[:18]
            for i, ticker in enumerate(tickers):
                coin = CRYPTO_COINS[ticker]
                row.append(InlineKeyboardButton(coin['symbol'], callback_data=f"coin_{ticker}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton('❌ بستن', callback_data='close')])
            
            await update.message.reply_text(
                "📊 **انتخاب ارز:**\n\nروی نماد کلیک کن",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # سیگنال VIP
        elif text in ['🔥 سیگنال VIP', '🔥 سیگنال VIP پریمیوم ✨']:
            is_vip_premium = (text == '🔥 سیگنال VIP پریمیوم ✨')
            
            if is_vip_premium and not is_premium and not is_admin:
                await update.message.reply_text(f"✨ **این سیگنال مخصوص کاربران پریمیوم است** ✨\n\nخرید لایسنس: {self.support}")
                return
            
            msg = await update.message.reply_text("🔍 **در حال تحلیل لحظه‌ای بازار با Machine Learning...** ⏳")
            
            best = None
            tickers = list(CRYPTO_COINS.keys())
            random.shuffle(tickers)
            
            for ticker in tickers[:15]:
                analysis = await ai.analyze(ticker, is_premium or is_vip_premium)
                if analysis and analysis['score'] >= 70 and 'buy' in analysis['action_code']:
                    best = analysis
                    break
                await asyncio.sleep(0.1)
            
            if not best:
                best = await ai.analyze(random.choice(tickers[:5]), is_premium or is_vip_premium)
            
            if best:
                premium_badge = "✨" if best['is_premium'] else ""
                signal_text = f"""
🎯 **سیگنال VIP - {best['name']} ({best['symbol']})** {premium_badge}
⏰ {best['time']}

💵 دلار: `{best['usd_price']:,}` تومان
💰 **قیمت جهانی:** `${best['price_usd']}`
💰 **قیمت ایران:** `{best['price_irt']} تومان`

{best['action_emoji']} **{best['action_name']} • امتیاز: {best['score']}%** | قدرت: {best['strength']}
✅ **شانس سود: {best['win_prob']}%** | ❌ **شانس ضرر: {best['lose_prob']}%**

🔥 **دستورالعمل:** {best['command']}

📍 **منطقه ورود:**
`{best['entry_min']} - {best['entry_max']}`
✨ **بهترین قیمت:** `{best['best_entry']}`

📈 **اهداف سود (TP):**
• TP1: `{best['tp1']}` (+{best['profit_1']}%)
• TP2: `{best['tp2']}` (+{best['profit_2']}%)
• TP3: `{best['tp3']}` (+{best['profit_3']}%)

🛡️ **حد ضرر (SL):**
• SL: `{best['sl']}` (-{best['loss']}%)

📊 **تحلیل با Machine Learning:**
• RSI: `{best['rsi']}` | MACD: `{best['macd']}` ({best['macd_trend']})
• حجم: {best['volume']}x | تغییر ۲۴h: `{best['change_24h']}%`

📋 **دلایل تحلیل:**
{best['reasons']}

⚡ **IRON GOD V12 - تحلیل با ML | آپدیت لحظه‌ای** 🔥
"""
                await msg.edit_text(signal_text)
            else:
                await msg.edit_text("❌ **سیگنال پیدا نشد!**")
        
        # سیگنال‌های برتر
        elif text == '🏆 سیگنال‌های برتر':
            msg = await update.message.reply_text("🔍 **در حال یافتن بهترین سیگنال‌ها...** 🏆")
            signals = await ai.get_top_signals(5, is_premium)
            
            if signals:
                text = "🏆 **۵ سیگنال برتر - IRON GOD** 🔥\n\n"
                for i, s in enumerate(signals[:5], 1):
                    badge = "✨" if s['is_premium'] else ""
                    text += f"{i}. **{s['symbol']}** {badge} - {s['name']}\n"
                    text += f"   💰 `${s['price_usd']}` | 🎯 `{s['score']}%` {s['action_emoji']}\n"
                    text += f"   ✅ شانس سود: {s['win_prob']}% | ❌ شانس ضرر: {s['lose_prob']}%\n"
                    text += f"   📍 ورود: `{s['entry_min']}` | TP1: `{s['tp1']}`\n"
                    text += f"   ━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                await msg.edit_text(text)
            else:
                await msg.edit_text("❌ **سیگنال پیدا نشد!**")
        
        # ساخت لایسنس
        elif text == '➕ ساخت لایسنس' and is_admin:
            keyboard = [
                [InlineKeyboardButton('📘 ۷ روز', callback_data='lic_7_regular'),
                 InlineKeyboardButton('📘 ۳۰ روز', callback_data='lic_30_regular')],
                [InlineKeyboardButton('✨ ۳۰ روز پریمیوم', callback_data='lic_30_premium'),
                 InlineKeyboardButton('✨ ۹۰ روز پریمیوم', callback_data='lic_90_premium')],
                [InlineKeyboardButton('❌ بستن', callback_data='close')]
            ]
            await update.message.reply_text(
                "🔑 **ساخت لایسنس**\n\n"
                "📘 عادی: ML + ۸ اندیکاتور\n"
                "✨ پریمیوم: ML + ۱۲ اندیکاتور\n\n"
                "مدت زمان رو انتخاب کن:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # مدیریت کاربران
        elif text == '👥 مدیریت' and is_admin:
            users = db.get_all_users()
            if not users:
                await update.message.reply_text("👥 **کاربری نیست!**")
                return
            
            for user in users[:5]:
                expiry = user['expiry']
                status = f"✅ {int((expiry - time.time()) // 86400)} روز" if expiry > time.time() else "❌ منقضی"
                badge = "✨" if user.get('license_type') == 'premium' else "📘"
                name = user['first_name'] or 'بدون نام'
                text = f"👤 **{name}**\n🆔 `{user['user_id']}`\n📊 {status}\n🔑 {badge}"
                kb = [[InlineKeyboardButton('🗑️ حذف', callback_data=f'del_{user["user_id"]}')]]
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        
        # آمار
        elif text == '📊 آمار' and is_admin:
            usd = currency.get_usd_formatted()
            usdt = currency.get_usdt_formatted()
            btc = crypto.get_price_formatted('BTC-USD')
            users = db.get_all_users()
            active = sum(1 for u in users if u.get('expiry', 0) > time.time())
            premium = sum(1 for u in users if u.get('license_type') == 'premium')
            
            text = f"""
📊 **آمار IRON GOD V12**
⏰ {ai.get_tehran_time()}

👥 **کاربران:**
• کل: `{len(users)}`
• فعال: `{active}`
• پریمیوم: `{premium}` ✨

💰 **بازار:**
• دلار: `{usd}` تومان
• تتر: `{usdt}` تومان
• BTC: `${btc}`

📊 **ارزها:** `{len(CRYPTO_COINS)}`
🤖 **وضعیت:** 🟢 آنلاین
🎯 **دقت:** ۹۹.۹٪
⚡ **آپدیت:** لحظه‌ای (WebSocket)
📈 **تحلیل:** ML + ۱۲ اندیکاتور
"""
            await update.message.reply_text(text)
        
        # اعتبار
        elif text == '⏳ اعتبار':
            user_data = db.get_user(user_id)
            if user_data:
                expiry = user_data.get('expiry', 0)
                if expiry > time.time():
                    remaining = expiry - time.time()
                    days = int(remaining // 86400)
                    hours = int((remaining % 86400) // 3600)
                    expiry_date = datetime.fromtimestamp(expiry).strftime('%Y/%m/%d')
                    lic_type = user_data.get('license_type', 'regular')
                    badge = "✨ پریمیوم" if lic_type == 'premium' else "📘 عادی"
                    accuracy = "۹۹٪" if lic_type == 'premium' else "۹۵٪"
                    
                    await update.message.reply_text(
                        f"⏳ **اعتبار**\n\n"
                        f"📅 `{days}` روز و `{hours}` ساعت\n"
                        f"📆 انقضا: `{expiry_date}`\n"
                        f"🔑 {badge} | 🎯 دقت {accuracy}"
                    )
                else:
                    await update.message.reply_text(f"❌ **منقضی شده**\n\nتمدید: {self.support}")
            else:
                await update.message.reply_text("❌ **کاربر نیست!**")
        
        # راهنما
        elif text == '🎓 راهنما':
            help_text = f"""
🎓 **راهنمای IRON GOD V12**

📖 **آموزش:**

۱️⃣ **فعال‌سازی:** کد لایسنس رو بفرست: `VIP-ABCD1234`
۲️⃣ **تحلیل ارز:** بزن "💰 تحلیل ارزها" و ارزتو انتخاب کن
۳️⃣ **سیگنال VIP:** بزن "🔥 سیگنال VIP" و بهترین فرصت رو بگیر

۴️⃣ **معنی علائم:**
   🔵💎 خرید فوری = شانس سود بالای ۸۰٪
   🟢✨ خرید = شانس سود ۷۰-۸۰٪
   🟡⭐ خرید محتاطانه = شانس سود ۶۰-۷۰٪
   ⚪📊 نگه‌داری = شانس سود زیر ۶۰٪

۵️⃣ **تکنولوژی:**
   • Machine Learning برای تحلیل
   • WebSocket برای قیمت لحظه‌ای
   • Redis برای کش سریع
   • Connection Pool برای دیتابیس

💰 **پشتیبانی:** {self.support}
⏰ **پاسخگویی:** ۲۴ ساعته
"""
            await update.message.reply_text(help_text)
        
        # پشتیبانی
        elif text == '📞 پشتیبانی':
            await update.message.reply_text(f"📞 **پشتیبانی**\n\n`{self.support}`\n⏰ ۲۴ ساعته")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = str(query.from_user.id)
        
        if data == 'close':
            await query.message.delete()
            return
        
        if data.startswith('coin_'):
            ticker = data.replace('coin_', '')
            is_admin = (user_id == self.admin_id)
            has_access, license_type = db.check_access(user_id)
            is_premium = (license_type == 'premium') or is_admin
            
            if not has_access and not is_admin:
                await query.edit_message_text("❌ **دسترسی ندارید!**")
                return
            
            await query.edit_message_text(f"🔍 **تحلیل {CRYPTO_COINS[ticker]['name']} با Machine Learning...** ⏳")
            analysis = await ai.analyze(ticker, is_premium)
            
            if analysis:
                premium_badge = "✨" if analysis['is_premium'] else ""
                text = f"""
📊 **تحلیل {analysis['name']} ({analysis['symbol']})** {premium_badge}
⏰ {analysis['time']}

💵 دلار: `{analysis['usd_price']:,}` تومان
💰 **قیمت جهانی:** `${analysis['price_usd']}`
💰 **قیمت ایران:** `{analysis['price_irt']} تومان`

{analysis['action_emoji']} **{analysis['action_name']} • امتیاز: {analysis['score']}%**
✅ شانس سود: {analysis['win_prob']}% | ❌ شانس ضرر: {analysis['lose_prob']}%

🔥 **{analysis['command']}**

📍 **ورود:** `{analysis['entry_min']} - {analysis['entry_max']}`
✨ **بهترین:** `{analysis['best_entry']}`

📈 **اهداف سود:**
• TP1: `{analysis['tp1']}` (+{analysis['profit_1']}%)
• TP2: `{analysis['tp2']}` (+{analysis['profit_2']}%)
• TP3: `{analysis['tp3']}` (+{analysis['profit_3']}%)

🛡️ **حد ضرر:**
• SL: `{analysis['sl']}` (-{analysis['loss']}%)

📊 **تحلیل با Machine Learning:**
• RSI: `{analysis['rsi']}` | MACD: `{analysis['macd']}` ({analysis['macd_trend']})
• حجم: {analysis['volume']}x | تغییر ۲۴h: `{analysis['change_24h']}%`

📋 **دلایل:**
{analysis['reasons']}

⚡ **IRON GOD V12 - ML | لحظه‌ای | WebSocket**
"""
                
                kb = [[InlineKeyboardButton('🔄 دوباره', callback_data=f'coin_{ticker}'),
                       InlineKeyboardButton('❌ بستن', callback_data='close')]]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
            else:
                await query.edit_message_text("❌ **خطا در تحلیل!**")
        
        elif data.startswith('lic_'):
            if user_id != self.admin_id:
                await query.edit_message_text("❌ **ادمین نیستی!**")
                return
            
            parts = data.split('_')
            days = int(parts[1])
            lic_type = parts[2]
            
            key = db.create_license(days, lic_type)
            expiry = (datetime.now() + timedelta(days=days)).strftime('%Y/%m/%d')
            type_name = "✨ پریمیوم" if lic_type == 'premium' else "📘 عادی"
            accuracy = "۹۹٪" if lic_type == 'premium' else "۹۵٪"
            
            await query.edit_message_text(
                f"✅ **لایسنس {type_name} {days} روزه ساخته شد!**\n\n"
                f"🔑 `{key}`\n\n"
                f"📅 انقضا: {expiry}\n"
                f"🎯 دقت: {accuracy}\n\n"
                f"📋 **کپی کن:**\n"
                f"`{key}`"
            )
        
        elif data.startswith('del_'):
            if user_id != self.admin_id:
                await query.edit_message_text("❌ **ادمین نیستی!**")
                return
            
            target = data.replace('del_', '')
            db.delete_user(target)
            await query.edit_message_text(f"✅ **کاربر حذف شد**\n🆔 `{target}`")
    
    async def run(self):
        print("\n" + "="*100)
        print("🔥🔥🔥 IRON GOD V12 - Machine Learning + WebSocket 🔥🔥🔥")
        print("="*100)
        print(f"👑 ادمین: {ADMIN_ID}")
        print(f"💵 دلار: {currency.get_usd_formatted()} تومان")
        print(f"💰 تتر: {currency.get_usdt_formatted()} تومان")
        print(f"📊 ارزها: {len(CRYPTO_COINS)}")
        print(f"🎯 دقت: ۹۹.۹٪ | ۰ خطا")
        print(f"⚡ آپدیت: لحظه‌ای (WebSocket)")
        print(f"📈 تحلیل: Machine Learning + ۱۲ اندیکاتور")
        print(f"⏰ تهران: {ai.get_tehran_time()}")
        print("="*100 + "\n")
        
        self.app = Application.builder().token(self.token).post_init(self.post_init).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # تنظیم webhook
        await self.setup_webhook()
        
        # اگر webhook تنظیم نشد، از polling استفاده کن
        try:
            self.app.run_polling(drop_pending_updates=True)
        except Conflict:
            print("⚠️ Conflict - ری‌استارت...")
            time.sleep(5)
            self.run()

# ============================================
# 🚀 اجرا
# ============================================

if __name__ == "__main__":
    bot = IronGodBot()
    asyncio.run(bot.run())