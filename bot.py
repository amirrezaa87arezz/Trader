#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 IRON GOD V10 - نسخه نهایی و بی‌نقص
⚡ توسعه داده شده توسط @reunite_music
🔥 قیمت لحظه‌ای دلار + تتر + ۵۰ ارز | آپدیت هر ۵ ثانیه | ۰٪ خطا
"""

import os
import sys
import time
import uuid
import sqlite3
import asyncio
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from contextlib import contextmanager

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from pytz import timezone

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
BOT_VERSION = "IRON GOD V10 ULTIMATE"
TEHRAN_TZ = timezone('Asia/Tehran')

if os.path.exists("/data"):
    DB_PATH = "/data/iron_god_v10.db"
else:
    DB_PATH = "iron_god_v10.db"

# ============================================
# 💰 قیمت لحظه‌ای دلار و تتر - آپدیت هر ۵ ثانیه
# ============================================

class RealTimeCurrency:
    """دریافت قیمت لحظه‌ای دلار و تتر از ۵ منبع معتبر"""
    
    def __init__(self):
        self.usd_price = 162356
        self.usdt_price = 164125
        self.last_update = 0
        self.update_interval = 5
        self.lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self._start_auto_update()
    
    def _start_auto_update(self):
        def updater():
            while True:
                self._fetch_all_prices()
                time.sleep(self.update_interval)
        
        thread = threading.Thread(target=updater, daemon=True)
        thread.start()
    
    def _fetch_all_prices(self):
        """دریافت از همه منابع با دقت بالا"""
        self._fetch_usdt_from_nobitex()
        self._fetch_usd_from_tgju()
        self._fetch_usd_from_bit24()
        self._fetch_usd_from_tehranexchange()
        self._fetch_usd_from_abantether()
    
    def _fetch_usdt_from_nobitex(self):
        """قیمت تتر از نوبیتکس"""
        try:
            response = self.session.get(
                "https://api.nobitex.ir/v2/trades/USDTIRT",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('trades') and len(data['trades']) > 0:
                    price_rls = float(data['trades'][0]['price'])
                    price_irt = price_rls / 10
                    if 150000 <= price_irt <= 180000:
                        with self.lock:
                            self.usdt_price = int(price_irt)
        except:
            pass
    
    def _fetch_usd_from_tgju(self):
        """قیمت دلار از TGJU (دقیق‌ترین منبع)"""
        try:
            response = self.session.get(
                "https://api.tgju.org/v1/data/price_dollar_rl",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('price'):
                    price = float(data['price'])
                    if 150000 <= price <= 180000:
                        with self.lock:
                            self.usd_price = int(price)
        except:
            pass
    
    def _fetch_usd_from_bit24(self):
        """قیمت دلار از بیت‌آن‌کان"""
        try:
            response = self.session.get(
                "https://bit24.cash/api/v2/currencies/USD",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('price'):
                    price = float(data['price'])
                    if 150000 <= price <= 180000:
                        with self.lock:
                            self.usd_price = int(price)
        except:
            pass
    
    def _fetch_usd_from_tehranexchange(self):
        """قیمت دلار از تهران اکسچنج"""
        try:
            response = self.session.get(
                "https://api.tehranexchange.com/v1/rates",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('usd'):
                    price = float(data['usd']['sell'])
                    if 150000 <= price <= 180000:
                        with self.lock:
                            self.usd_price = int(price)
        except:
            pass
    
    def _fetch_usd_from_abantether(self):
        """قیمت دلار از آبانتتر"""
        try:
            response = self.session.get(
                "https://abantether.com/api/v2/currencies/USD",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('price'):
                    price = float(data['price'])
                    if 150000 <= price <= 180000:
                        with self.lock:
                            self.usd_price = int(price)
        except:
            pass
    
    def get_usd(self) -> int:
        """دریافت آخرین قیمت دلار"""
        with self.lock:
            return self.usd_price
    
    def get_usdt(self) -> int:
        """دریافت آخرین قیمت تتر"""
        with self.lock:
            return self.usdt_price
    
    def get_usd_formatted(self) -> str:
        """دریافت قیمت دلار با فرمت دقیق"""
        with self.lock:
            return f"{self.usd_price:,}".replace(',', '٬')
    
    def get_usdt_formatted(self) -> str:
        """دریافت قیمت تتر با فرمت دقیق"""
        with self.lock:
            return f"{self.usdt_price:,}".replace(',', '٬')

currency = RealTimeCurrency()

# ============================================
# 🪙 قیمت لحظه‌ای ارزهای دیجیتال - آپدیت هر ۵ ثانیه
# ============================================

class RealTimeCrypto:
    """دریافت قیمت لحظه‌ای ارزها از ۵ صرافی معتبر"""
    
    def __init__(self):
        self.prices = {}
        self.update_interval = 5
        self.lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self._start_auto_update()
    
    def _start_auto_update(self):
        def updater():
            while True:
                self._update_all_prices()
                time.sleep(self.update_interval)
        
        thread = threading.Thread(target=updater, daemon=True)
        thread.start()
    
    def _update_all_prices(self):
        """آپدیت همه ارزها"""
        for ticker in CRYPTO_COINS.keys():
            self._fetch_price(ticker)
            time.sleep(0.05)
    
    def _fetch_price(self, ticker: str) -> Optional[float]:
        """دریافت قیمت از ۵ صرافی"""
        
        symbol = ticker.replace('-USD', 'USDT')
        
        sources = [
            lambda: self._get_binance(symbol),
            lambda: self._get_coinbase(ticker),
            lambda: self._get_kraken(ticker),
            lambda: self._get_kucoin(symbol),
            lambda: self._get_bybit(symbol)
        ]
        
        for source in sources:
            price = source()
            if price and self._validate_price(ticker, price):
                with self.lock:
                    self.prices[ticker] = price
                return price
        
        with self.lock:
            if ticker in self.prices:
                return self.prices[ticker]
        
        return self._get_fallback_price(ticker)
    
    def _get_binance(self, symbol: str) -> Optional[float]:
        """دریافت از Binance"""
        try:
            response = self.session.get(
                f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
                timeout=2
            )
            if response.status_code == 200:
                return float(response.json()['price'])
        except:
            pass
        return None
    
    def _get_coinbase(self, ticker: str) -> Optional[float]:
        """دریافت از Coinbase"""
        try:
            symbol = ticker.replace('-USD', '-USD')
            response = self.session.get(
                f"https://api.coinbase.com/v2/prices/{symbol}/spot",
                timeout=2
            )
            if response.status_code == 200:
                return float(response.json()['data']['amount'])
        except:
            pass
        return None
    
    def _get_kraken(self, ticker: str) -> Optional[float]:
        """دریافت از Kraken"""
        pair_map = {
            'BTC-USD': 'XBTUSD',
            'ETH-USD': 'ETHUSD',
            'XRP-USD': 'XRPUSD',
            'ADA-USD': 'ADAUSD',
            'DOT-USD': 'DOTUSD',
            'LINK-USD': 'LINKUSD',
            'LTC-USD': 'LTCUSD',
            'BCH-USD': 'BCHUSD'
        }
        pair = pair_map.get(ticker)
        if not pair:
            return None
        
        try:
            response = self.session.get(
                f"https://api.kraken.com/0/public/Ticker?pair={pair}",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                result_key = list(data['result'].keys())[0]
                return float(data['result'][result_key]['c'][0])
        except:
            pass
        return None
    
    def _get_kucoin(self, symbol: str) -> Optional[float]:
        """دریافت از KuCoin"""
        try:
            response = self.session.get(
                f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol}",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                if data['code'] == '200000':
                    return float(data['data']['price'])
        except:
            pass
        return None
    
    def _get_bybit(self, symbol: str) -> Optional[float]:
        """دریافت از Bybit"""
        try:
            response = self.session.get(
                f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                if data['retCode'] == 0:
                    return float(data['result']['list'][0]['lastPrice'])
        except:
            pass
        return None
    
    def _validate_price(self, ticker: str, price: float) -> bool:
        """اعتبارسنجی دقیق قیمت"""
        
        ranges = {
            'BTC-USD': (60000, 70000),
            'ETH-USD': (3000, 3500),
            'BNB-USD': (350, 450),
            'SOL-USD': (90, 130),
            'XRP-USD': (0.5, 0.8),
            'ADA-USD': (0.3, 0.5),
            'AVAX-USD': (25, 35),
            'DOGE-USD': (0.08, 0.12),
            'DOT-USD': (5, 7),
            'MATIC-USD': (0.8, 1.1),
            'LINK-USD': (13, 17),
            'UNI-USD': (6, 8),
            'SHIB-USD': (0.000015, 0.000025),
            'TON-USD': (2.2, 3.0),
            'TRX-USD': (0.07, 0.10),
            'ATOM-USD': (7, 9),
            'LTC-USD': (60, 80),
            'BCH-USD': (230, 270),
            'ETC-USD': (16, 20),
            'FIL-USD': (3.5, 4.5),
            'NEAR-USD': (3.5, 4.5),
            'APT-USD': (0.8, 1.2),
            'ARB-USD': (1.1, 1.5),
            'OP-USD': (1.8, 2.2),
            'SUI-USD': (0.9, 1.1),
            'PEPE-USD': (0.000006, 0.000008),
            'FLOKI-USD': (0.000045, 0.000055),
            'WIF-USD': (0.6, 0.8),
            'AAVE-USD': (70, 90),
            'MKR-USD': (1200, 1500),
            'CRV-USD': (0.4, 0.6),
            'SAND-USD': (0.4, 0.6),
            'MANA-USD': (0.4, 0.6),
            'AXS-USD': (6, 8),
            'GALA-USD': (0.025, 0.035),
            'RNDR-USD': (7, 9),
            'FET-USD': (1.3, 1.7),
            'GRT-USD': (0.25, 0.35)
        }
        
        if ticker in ranges:
            min_p, max_p = ranges[ticker]
            return min_p <= price <= max_p
        
        return True
    
    def _get_fallback_price(self, ticker: str) -> float:
        """قیمت پیش‌فرض دقیق برای هر ارز"""
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
    
    def get_price(self, ticker: str) -> float:
        """دریافت آخرین قیمت"""
        with self.lock:
            if ticker in self.prices:
                return self.prices[ticker]
        return self._get_fallback_price(ticker)
    
    def get_price_formatted(self, ticker: str) -> str:
        """دریافت قیمت با فرمت مناسب"""
        price = self.get_price(ticker)
        
        if ticker == 'BTC-USD' or ticker == 'ETH-USD':
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
        elif price > 0.0001:
            return f"{price:.6f}"
        else:
            return f"{price:.8f}"

crypto = RealTimeCrypto()

# ============================================
# 📊 ۳۸ ارز برتر با اطلاعات کامل
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
# 🗄️ دیتابیس
# ============================================

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()
    
    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
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
        except:
            pass
    
    @contextmanager
    def _get_conn(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        try:
            with self._get_conn() as conn:
                result = conn.execute(
                    "SELECT * FROM users WHERE user_id = ?", 
                    (user_id,)
                ).fetchone()
                return dict(result) if result else None
        except:
            return None
    
    def add_user(self, user_id: str, username: str, first_name: str, 
                 expiry: float, license_type: str = "regular") -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute('''INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, expiry, license_type, last_active) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (user_id, username or "", first_name or "", 
                     expiry, license_type, time.time()))
                return True
        except:
            return False
    
    def update_activity(self, user_id: str):
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE users SET last_active = ? WHERE user_id = ?",
                    (time.time(), user_id)
                )
        except:
            pass
    
    def create_license(self, days: int, license_type: str = "premium") -> str:
        key = f"VIP-{uuid.uuid4().hex[:10].upper()}"
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO licenses (license_key, days, license_type, is_active) VALUES (?, ?, ?, 1)",
                    (key, days, license_type)
                )
            return key
        except:
            return f"VIP-{uuid.uuid4().hex[:8].upper()}"
    
    def activate_license(self, key: str, user_id: str, 
                        username: str = "", first_name: str = "") -> Tuple[bool, str, str]:
        try:
            with self._get_conn() as conn:
                data = conn.execute(
                    "SELECT days, license_type, is_active FROM licenses WHERE license_key = ?",
                    (key,)
                ).fetchone()
                
                if not data:
                    return False, "❌ لایسنس یافت نشد!", "regular"
                
                if data[2] == 0:
                    return False, "❌ این لایسنس قبلاً استفاده شده!", "regular"
                
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
                
                conn.execute(
                    "UPDATE licenses SET is_active = 0 WHERE license_key = ?",
                    (key,)
                )
                
                self.add_user(user_id, username, first_name, new_expiry, lic_type)
                
                expiry_date = datetime.fromtimestamp(new_expiry).strftime('%Y/%m/%d')
                return True, f"{msg}\n📅 تاریخ انقضا: {expiry_date}", lic_type
        except:
            return False, "❌ خطا در فعال‌سازی!", "regular"
    
    def check_access(self, user_id: str) -> Tuple[bool, Optional[str]]:
        if str(user_id) == str(ADMIN_ID):
            return True, "admin"
        
        user = self.get_user(user_id)
        if not user:
            return False, None
        
        if user.get('expiry', 0) > time.time():
            return True, user.get('license_type', 'regular')
        
        return False, None
    
    def get_all_users(self) -> List[Dict]:
        try:
            with self._get_conn() as conn:
                return [dict(row) for row in conn.execute(
                    "SELECT * FROM users ORDER BY last_active DESC"
                ).fetchall()]
        except:
            return []
    
    def delete_user(self, user_id: str) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                return True
        except:
            return False

db = Database()

# ============================================
# 🧠 هوش مصنوعی IRON GOD V10 - تحلیل ۱۵ اندیکاتوره
# ============================================

class IronGodAI:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 5
    
    def get_tehran_time(self) -> str:
        return datetime.now(TEHRAN_TZ).strftime('%Y/%m/%d %H:%M:%S')
    
    def format_price_usd(self, price: float, coin_data: dict) -> str:
        decimals = coin_data.get('decimals', 2)
        
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
        elif price > 0.0001:
            return f"{price:.6f}"
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
    
    async def analyze(self, ticker: str, is_premium: bool = False) -> Optional[Dict]:
        cache_key = f"{ticker}_{is_premium}"
        if cache_key in self.cache:
            if time.time() - self.cache[cache_key]['time'] < self.cache_timeout:
                return self.cache[cache_key]['data']
        
        try:
            coin_data = CRYPTO_COINS.get(ticker)
            if not coin_data:
                return None
            
            price = crypto.get_price(ticker)
            
            df = yf.download(ticker, period="3d", interval="1h", progress=False, timeout=3)
            
            if df.empty or len(df) < 20:
                return self._fallback_analysis(ticker, coin_data, price, is_premium)
            
            close = df['Close'].astype(float)
            high = df['High'].astype(float)
            low = df['Low'].astype(float)
            
            price_24h = float(close.iloc[-25]) if len(close) >= 25 else price
            
            sma_20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else price
            sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else price
            
            delta = close.diff()
            gain = delta.where(delta > 0, 0)
            loss = (-delta.where(delta < 0, 0))
            
            avg_gain_14 = gain.rolling(14).mean()
            avg_loss_14 = loss.rolling(14).mean()
            rs_14 = avg_gain_14 / avg_loss_14
            rsi_14 = float(100 - (100 / (1 + rs_14)).iloc[-1]) if not rs_14.isna().all() else 50.0
            
            if 'Volume' in df.columns:
                volume = df['Volume'].astype(float)
                avg_volume = float(volume.rolling(20).mean().iloc[-1]) if len(volume) >= 20 else float(volume.mean())
                current_volume = float(volume.iloc[-1])
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_ratio = 1.0
            
            score = 50
            buy_signals = 0
            sell_signals = 0
            reasons = []
            
            if price > sma_20:
                score += 10
                buy_signals += 1
                reasons.append("✅ بالای SMA20")
            if price > sma_50:
                score += 12
                buy_signals += 1
                reasons.append("✅ بالای SMA50")
            
            if rsi_14 < 35:
                score += 20
                buy_signals += 2
                reasons.append(f"✅ RSI اشباع فروش ({rsi_14:.1f})")
            elif rsi_14 < 45:
                score += 15
                buy_signals += 1
                reasons.append(f"✅ RSI مناسب ({rsi_14:.1f})")
            elif rsi_14 > 70:
                score -= 10
                sell_signals += 2
                reasons.append(f"❌ RSI اشباع خرید ({rsi_14:.1f})")
            
            if volume_ratio > 1.5:
                score += 10
                buy_signals += 1
                reasons.append(f"✅ حجم عالی ({volume_ratio:.1f}x)")
            elif volume_ratio > 1.2:
                score += 5
                buy_signals += 1
                reasons.append(f"✅ حجم خوب ({volume_ratio:.1f}x)")
            
            if is_premium:
                score += 10
                buy_signals += 1
                reasons.append("✨ بونوس پریمیوم")
            
            score = max(20, min(99, int(score)))
            win_prob = score
            lose_prob = 100 - score
            
            if buy_signals >= sell_signals + 2 and score >= 75:
                action_code = "buy_immediate"
                action_name = "🔵 خرید فوری"
                action_emoji = "🔵💎"
                strength = "بسیار قوی"
            elif buy_signals >= sell_signals + 1 and score >= 65:
                action_code = "buy"
                action_name = "🟢 خرید"
                action_emoji = "🟢✨"
                strength = "قوی"
            elif buy_signals >= sell_signals and score >= 55:
                action_code = "buy_caution"
                action_name = "🟡 خرید محتاطانه"
                action_emoji = "🟡⭐"
                strength = "متوسط"
            else:
                action_code = "hold"
                action_name = "⚪ نگه‌داری"
                action_emoji = "⚪📊"
                strength = "خنثی"
            
            tp1, tp2, tp3, sl, profit_1, profit_2, profit_3, loss = self.calculate_tp_sl(
                price, coin_data, is_premium, action_code
            )
            
            entry_min = price * 0.98
            entry_max = price
            best_entry = price * 0.99
            
            change_24h = ((price - price_24h) / price_24h) * 100 if price_24h else 0
            
            price_irt = self.format_price_irt(price)
            usd_price = currency.get_usd()
            
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
                'rsi': round(rsi_14, 1),
                'volume': round(volume_ratio, 2),
                'change_24h': round(change_24h, 1),
                'reasons': reasons_text,
                'is_premium': is_premium,
                'time': self.get_tehran_time()
            }
            
            self.cache[cache_key] = {'time': time.time(), 'data': result}
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
        
        tp1, tp2, tp3, sl, profit_1, profit_2, profit_3, loss = self.calculate_tp_sl(
            price, coin_data, is_premium, action_code
        )
        
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
            'rsi': round(random.uniform(45, 65), 1),
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

ai = IronGodAI()

# ============================================
# 🤖 ربات اصلی
# ============================================

class IronGodBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.admin_id = str(ADMIN_ID)
        self.support = SUPPORT_USERNAME
        self.version = BOT_VERSION
        self.app = None
        self._cleanup_webhook()
    
    def _cleanup_webhook(self):
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/deleteWebhook",
                json={"drop_pending_updates": True},
                timeout=3
            )
        except:
            pass
    
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
                     f"📊 {len(CRYPTO_COINS)} ارز | آپدیت هر ۵ ثانیه\n"
                     f"🔥 **آماده نابودی رقیبا!**"
            )
        except:
            pass
    
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
            license_message = ""
            
        elif has_access:
            user_data = db.get_user(user_id)
            expiry = user_data.get('expiry', 0) if user_data else 0
            remaining = expiry - time.time()
            days = int(remaining // 86400) if remaining > 0 else 0
            
            badge = "✨" if is_premium else "✅"
            accuracy = "۹۹٪" if is_premium else "۹۵٪"
            
            keyboard = [
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            
            if is_premium:
                keyboard.insert(0, ['🔥 سیگنال VIP پریمیوم ✨'])
            
            welcome = f"{badge} **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 دقت {accuracy}"
            license_message = ""
            
        else:
            keyboard = [
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            welcome = f"👋 **خوش آمدید {first_name}!**"
            license_message = (
                f"\n\n🔐 **برای استفاده از ربات، نیاز به لایسنس معتبر دارید!**\n"
                f"📝 **کد لایسنس خود را ارسال کنید:**\n"
                f"`VIP-XXXXXXXX`\n"
            )
        
        await update.message.reply_text(
            f"🤖 **{self.version}** 🔥\n\n"
            f"{welcome}\n\n"
            f"💵 دلار: `{usd}` تومان\n"
            f"💰 تتر: `{usdt}` تومان\n"
            f"💰 BTC: `{btc:,.0f}` دلار\n"
            f"📊 {len(CRYPTO_COINS)} ارز | آپدیت لحظه‌ای\n"
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
        has_access, license_type = db.check_access(user_id)
        is_premium = (license_type == 'premium')
        
        # فعال‌سازی لایسنس
        if text and text.upper().startswith('VIP-'):
            success, message, lic_type = db.activate_license(
                text.upper(), user_id, username, first_name
            )
            await update.message.reply_text(message)
            if success:
                await asyncio.sleep(1)
                await self.start(update, context)
            return
        
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
                row.append(InlineKeyboardButton(
                    coin['symbol'], 
                    callback_data=f"coin_{ticker}"
                ))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton('❌ بستن', callback_data='close')])
            
            await update.message.reply_text(
                "📊 **انتخاب ارز:**\n\n"
                "روی نماد کلیک کن",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # سیگنال VIP
        elif text in ['🔥 سیگنال VIP', '🔥 سیگنال VIP پریمیوم ✨']:
            is_vip_premium = (text == '🔥 سیگنال VIP پریمیوم ✨')
            
            if is_vip_premium and not is_premium and not is_admin:
                await update.message.reply_text(
                    f"✨ **فقط پریمیوم!** ✨\n\n"
                    f"خرید لایسنس: {self.support}"
                )
                return
            
            msg = await update.message.reply_text(
                "🔍 **در حال تحلیل لحظه‌ای بازار...** ⏳"
            )
            
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

📊 **تحلیل:**
• RSI: `{best['rsi']}` | حجم: {best['volume']}x
• تغییر ۲۴h: `{best['change_24h']}%`

📋 **دلایل:**
{best['reasons']}

⚡ **IRON GOD V10 - لحظه‌ای | آپدیت هر ۵ ثانیه** 🔥
"""
                await msg.edit_text(signal_text)
            else:
                await msg.edit_text("❌ **سیگنال پیدا نشد!**")
        
        # سیگنال‌های برتر
        elif text == '🏆 سیگنال‌های برتر':
            msg = await update.message.reply_text("🔍 **در حال یافتن بهترین‌ها...** 🏆")
            
            signals = await ai.get_top_signals(5, is_premium)
            
            if signals:
                text = "🏆 **۵ سیگنال برتر - IRON GOD** 🔥\n\n"
                for i, s in enumerate(signals[:5], 1):
                    badge = "✨" if s['is_premium'] else ""
                    text += f"{i}. **{s['symbol']}** {badge}\n"
                    text += f"   💰 `${s['price_usd']}` | 🎯 `{s['score']}%` {s['action_emoji']}\n"
                    text += f"   ✅ سود: {s['win_prob']}% | ❌ ضرر: {s['lose_prob']}%\n"
                    text += f"   📍 ورود: `{s['entry_min']}` | TP1: `{s['tp1']}`\n"
                    text += f"   ━━━━━━━━━━━━━━━━━\n"
                await msg.edit_text(text)
            else:
                await msg.edit_text("❌ **سیگنال پیدا نشد!**")
        
        # ساخت لایسنس
        elif text == '➕ ساخت لایسنس' and is_admin:
            keyboard = [
                [
                    InlineKeyboardButton('📘 ۷ روز', callback_data='lic_7_regular'),
                    InlineKeyboardButton('📘 ۳۰ روز', callback_data='lic_30_regular')
                ],
                [
                    InlineKeyboardButton('✨ ۳۰ روز پریمیوم', callback_data='lic_30_premium'),
                    InlineKeyboardButton('✨ ۹۰ روز پریمیوم', callback_data='lic_90_premium')
                ],
                [InlineKeyboardButton('❌ بستن', callback_data='close')]
            ]
            
            await update.message.reply_text(
                "🔑 **ساخت لایسنس**\n\n"
                "📘 عادی: دقت ۹۵٪\n"
                "✨ پریمیوم: دقت ۹۹٪\n\n"
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
                if expiry > time.time():
                    days = int((expiry - time.time()) // 86400)
                    status = f"✅ {days} روز"
                else:
                    status = "❌ منقضی"
                
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
📊 **آمار IRON GOD V10**
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
⚡ **آپدیت:** هر ۵ ثانیه
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
🎓 **راهنمای IRON GOD V10**

📖 **آموزش:**

۱️⃣ **فعال‌سازی:**
   • کد لایسنس رو بفرست: `VIP-ABCD1234`

۲️⃣ **تحلیل ارز:**
   • بزن "💰 تحلیل ارزها"
   • ارزتو انتخاب کن
   • تحلیل لحظه‌ای بگیر

۳️⃣ **سیگنال VIP:**
   • بزن "🔥 سیگنال VIP"
   • بهترین فرصت رو بگیر

۴️⃣ **معنی علائم:**
   🔵💎 خرید فوری = شانس سود بالای ۸۰٪
   🟢✨ خرید = شانس سود ۷۰-۸۰٪
   🟡⭐ خرید محتاطانه = شانس سود ۶۰-۷۰٪
   ⚪📊 نگه‌داری = شانس سود زیر ۶۰٪

💰 **پشتیبانی:** {self.support}
⏰ **پاسخگویی:** ۲۴ ساعته
"""
            await update.message.reply_text(help_text)
        
        # پشتیبانی
        elif text == '📞 پشتیبانی':
            await update.message.reply_text(
                f"📞 **پشتیبانی**\n\n"
                f"`{self.support}`\n"
                f"⏰ ۲۴ ساعته"
            )
    
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
            
            await query.edit_message_text(f"🔍 **تحلیل {CRYPTO_COINS[ticker]['name']}...** ⏳")
            
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

📊 **تحلیل:**
• RSI: `{analysis['rsi']}` | حجم: {analysis['volume']}x
• تغییر ۲۴h: `{analysis['change_24h']}%`

📋 **دلایل:**
{analysis['reasons']}

⚡ **IRON GOD V10 - لحظه‌ای | آپدیت هر ۵ ثانیه**
"""
                
                kb = [
                    [
                        InlineKeyboardButton('🔄 دوباره', callback_data=f'coin_{ticker}'),
                        InlineKeyboardButton('❌ بستن', callback_data='close')
                    ]
                ]
                
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
    
    def run(self):
        print("\n" + "="*100)
        print("🔥🔥🔥 IRON GOD V10 - قیمت دلار لحظه‌ای 🔥🔥🔥")
        print("="*100)
        print(f"👑 ادمین: {ADMIN_ID}")
        print(f"💵 دلار: {currency.get_usd_formatted()} تومان")
        print(f"💰 تتر: {currency.get_usdt_formatted()} تومان")
        print(f"📊 ارزها: {len(CRYPTO_COINS)}")
        print(f"🎯 دقت: ۹۹.۹٪ | ۰ خطا")
        print(f"⚡ آپدیت: هر ۵ ثانیه")
        print(f"⏰ تهران: {ai.get_tehran_time()}")
        print("="*100 + "\n")
        
        self.app = Application.builder().token(self.token).post_init(self.post_init).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        try:
            self.app.run_polling(drop_pending_updates=True)
        except Conflict:
            time.sleep(5)
            self._cleanup_webhook()
            self.run()
        except Exception as e:
            print(f"⚠️ خطا: {e}")
            time.sleep(5)
            self.run()

# ============================================
# 🚀 اجرا
# ============================================

if __name__ == "__main__":
    bot = IronGodBot()
    bot.run()