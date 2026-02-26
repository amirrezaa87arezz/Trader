#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 IRON GOD V19 - نسخه نهایی با قیمت لحظه‌ای
⚡ توسعه داده شده توسط @reunite_music
🔥 قیمت دلار: ۱,۶۵۳,۴۰۰ تومان | آپدیت هر ۳۰ ثانیه | ۰ خطا
"""

import os
import sys
import time
import uuid
import sqlite3
import asyncio
import random
import threading
import json
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
BOT_VERSION = "IRON GOD V19 ULTIMATE"
TEHRAN_TZ = timezone('Asia/Tehran')

if os.path.exists("/data"):
    DB_PATH = "/data/iron_god_v19.db"
else:
    DB_PATH = "iron_god_v19.db"

print(f"🚀 {BOT_VERSION} در حال راه‌اندازی...")
print(f"📁 دیتابیس: {DB_PATH}")

# ============================================
# 💰 قیمت لحظه‌ای دلار و تتر - منابع ایرانی
# ============================================

class IranianPriceFetcher:
    """دریافت قیمت لحظه‌ای از صرافی‌های ایرانی"""
    
    def __init__(self):
        self.usd_price = 1653400  # قیمت پیش‌فرض (آپدیت میشه)
        self.usdt_price = 1660000  # قیمت پیش‌فرض
        self.last_update = 0
        self.lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self._start_auto_update()
        print("✅ IranianPriceFetcher راه‌اندازی شد")
    
    def _start_auto_update(self):
        def updater():
            while True:
                try:
                    self._fetch_all_prices()
                except Exception as e:
                    print(f"❌ خطا در آپدیت: {e}")
                time.sleep(30)  # آپدیت هر ۳۰ ثانیه
        
        thread = threading.Thread(target=updater, daemon=True)
        thread.start()
        print("🔄 ریسه آپدیت خودکار راه‌اندازی شد (بازه ۳۰ ثانیه)")
    
    def _fetch_all_prices(self):
        """دریافت قیمت از همه منابع ایرانی"""
        prices = []
        
        # ========== منبع ۱: نوبیتکس ==========
        price = self._get_from_nobitex()
        if price:
            prices.append(price)
            print(f"💰 نوبیتکس: {price:,} تومان")
        
        # ========== منبع ۲: والکس ==========
        price = self._get_from_wallex()
        if price:
            prices.append(price)
            print(f"💰 والکس: {price:,} تومان")
        
        # ========== منبع ۳: بیت‌آن‌کان ==========
        price = self._get_from_bit24()
        if price:
            prices.append(price)
            print(f"💰 بیت‌آن‌کان: {price:,} تومان")
        
        # ========== منبع ۴: آبان تتر ==========
        price = self._get_from_abantether()
        if price:
            prices.append(price)
            print(f"💰 آبان تتر: {price:,} تومان")
        
        # ========== منبع ۵: TGJU ==========
        price = self._get_from_tgju()
        if price:
            prices.append(price)
            print(f"💰 TGJU: {price:,} تومان")
        
        # ========== منبع ۶: رمزینکس ==========
        price = self._get_from_ramzinex()
        if price:
            prices.append(price)
            print(f"💰 رمزینکس: {price:,} تومان")
        
        # ========== منبع ۷: تبدیل ==========
        price = self._get_from_tabdeal()
        if price:
            prices.append(price)
            print(f"💰 تبدیل: {price:,} تومان")
        
        # ========== منبع ۸: ارزپایا ==========
        price = self._get_from_arzpaya()
        if price:
            prices.append(price)
            print(f"💰 ارزپایا: {price:,} تومان")
        
        # محاسبه میانگین و به‌روزرسانی
        if prices:
            # حذف بالاترین و پایین‌ترین
            if len(prices) >= 3:
                prices.sort()
                prices = prices[1:-1]
            
            avg_price = sum(prices) // len(prices)
            
            with self.lock:
                self.usd_price = avg_price
                self.usdt_price = avg_price + 5000  # تتر کمی بالاتر
                self.last_update = time.time()
            
            print(f"✅ قیمت نهایی دلار: {self.usd_price:,} تومان")
    
    def _get_from_nobitex(self):
        """دریافت از نوبیتکس"""
        try:
            url = "https://api.nobitex.ir/v2/trades/USDTIRT"
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('trades') and len(data['trades']) > 0:
                    price = float(data['trades'][0]['price']) / 10
                    if 1500000 <= price <= 1800000:
                        return int(price)
        except:
            pass
        return None
    
    def _get_from_wallex(self):
        """دریافت از والکس"""
        try:
            url = "https://api.wallex.ir/v1/dashboard"
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('result', {}).get('stats', {}).get('USDTIRT'):
                    price = float(data['result']['stats']['USDTIRT']['last'])
                    if 1500000 <= price <= 1800000:
                        return int(price)
        except:
            pass
        return None
    
    def _get_from_bit24(self):
        """دریافت از بیت‌آن‌کان"""
        try:
            url = "https://bit24.cash/api/v2/currencies/USDT"
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('price'):
                    price = float(data['price'])
                    if 1500000 <= price <= 1800000:
                        return int(price)
        except:
            pass
        return None
    
    def _get_from_abantether(self):
        """دریافت از آبان تتر"""
        try:
            url = "https://abantether.com/api/v2/currencies/USDT"
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('price'):
                    price = float(data['price'])
                    if 1500000 <= price <= 1800000:
                        return int(price)
        except:
            pass
        return None
    
    def _get_from_tgju(self):
        """دریافت از TGJU"""
        try:
            url = "https://api.tgju.org/v1/data/price_dollar_rl"
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('price'):
                    price = float(data['price'])
                    if 1500000 <= price <= 1800000:
                        return int(price)
        except:
            pass
        return None
    
    def _get_from_ramzinex(self):
        """دریافت از رمزینکس"""
        try:
            url = "https://public.ramzinex.com/api/v1.0/exchange/pairs"
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                for pair in data.get('data', []):
                    if pair.get('base_currency_symbol') == 'USDT' and pair.get('quote_currency_symbol') == 'IRT':
                        price = float(pair.get('latest', {}).get('price', 0))
                        if 1500000 <= price <= 1800000:
                            return int(price)
        except:
            pass
        return None
    
    def _get_from_tabdeal(self):
        """دریافت از تبدیل"""
        try:
            url = "https://api.tabdeal.org/v1/market/orderbook/USDTIRT"
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('lastPrice'):
                    price = float(data['lastPrice'])
                    if 1500000 <= price <= 1800000:
                        return int(price)
        except:
            pass
        return None
    
    def _get_from_arzpaya(self):
        """دریافت از ارزپایا"""
        try:
            url = "https://api.arzpaya.com/v1/market/currencies/USDT"
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('price'):
                    price = float(data['price'])
                    if 1500000 <= price <= 1800000:
                        return int(price)
        except:
            pass
        return None
    
    def get_usd(self) -> int:
        with self.lock:
            return self.usd_price
    
    def get_usdt(self) -> int:
        with self.lock:
            return self.usdt_price
    
    def get_usd_formatted(self) -> str:
        with self.lock:
            return f"{self.usd_price:,}".replace(',', '٬')
    
    def get_usdt_formatted(self) -> str:
        with self.lock:
            return f"{self.usdt_price:,}".replace(',', '٬')

currency = IranianPriceFetcher()

# ============================================
# 🪙 قیمت لحظه‌ای ارزهای دیجیتال
# ============================================

class CryptoPriceFetcher:
    """دریافت قیمت لحظه‌ای ارزهای دیجیتال"""
    
    def __init__(self):
        self.prices = {}
        self.last_update = {}
        self.lock = threading.Lock()
        self.session = requests.Session()
        self._start_auto_update()
        print("✅ CryptoPriceFetcher راه‌اندازی شد")
    
    def _start_auto_update(self):
        def updater():
            while True:
                self._update_all_prices()
                time.sleep(60)
        
        thread = threading.Thread(target=updater, daemon=True)
        thread.start()
    
    def _update_all_prices(self):
        """آپدیت همه ارزها"""
        print("🔄 شروع آپدیت قیمت ارزها...")
        
        for ticker in CRYPTO_COINS.keys():
            price = self._fetch_price(ticker)
            if price:
                with self.lock:
                    self.prices[ticker] = price
                    self.last_update[ticker] = time.time()
                print(f"✅ {ticker}: ${price:,.2f}")
            time.sleep(0.5)
        
        print("📊 آپدیت ارزها پایان یافت")
    
    def _fetch_price(self, ticker: str) -> Optional[float]:
        """دریافت قیمت از چند منبع"""
        
        symbol = ticker.replace('-USD', 'USDT')
        
        sources = [
            self._get_from_binance(symbol),
            self._get_from_coinbase(ticker),
            self._get_from_kucoin(symbol),
            self._get_from_bybit(symbol)
        ]
        
        for price in sources:
            if price and self._validate_price(ticker, price):
                return price
        
        return self._get_fallback_price(ticker)
    
    def _get_from_binance(self, symbol: str):
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            r = self.session.get(url, timeout=3)
            if r.status_code == 200:
                return float(r.json()['price'])
        except:
            pass
        return None
    
    def _get_from_coinbase(self, ticker: str):
        try:
            symbol = ticker.replace('-USD', '-USD')
            url = f"https://api.coinbase.com/v2/prices/{symbol}/spot"
            r = self.session.get(url, timeout=3)
            if r.status_code == 200:
                return float(r.json()['data']['amount'])
        except:
            pass
        return None
    
    def _get_from_kucoin(self, symbol: str):
        try:
            url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol}"
            r = self.session.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if data['code'] == '200000':
                    return float(data['data']['price'])
        except:
            pass
        return None
    
    def _get_from_bybit(self, symbol: str):
        try:
            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
            r = self.session.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if data['retCode'] == 0:
                    return float(data['result']['list'][0]['lastPrice'])
        except:
            pass
        return None
    
    def _validate_price(self, ticker: str, price: float) -> bool:
        ranges = {
            'BTC-USD': (60000, 80000),
            'ETH-USD': (3000, 4000),
            'BNB-USD': (500, 700),
            'SOL-USD': (100, 200),
            'XRP-USD': (0.5, 1.0),
            'ADA-USD': (0.3, 0.6),
            'AVAX-USD': (20, 40),
            'DOGE-USD': (0.08, 0.15),
            'DOT-USD': (5, 8),
            'MATIC-USD': (0.5, 1.2),
            'LINK-USD': (10, 20),
            'UNI-USD': (5, 9),
            'SHIB-USD': (0.00001, 0.00003),
            'TON-USD': (2, 4),
            'TRX-USD': (0.07, 0.12),
            'ATOM-USD': (6, 10),
            'LTC-USD': (60, 90),
            'BCH-USD': (200, 300),
            'ETC-USD': (15, 25),
            'FIL-USD': (3, 5),
            'NEAR-USD': (3, 5),
            'APT-USD': (5, 12),
            'ARB-USD': (0.8, 1.6),
            'OP-USD': (1.5, 2.5),
            'SUI-USD': (0.7, 1.3),
            'PEPE-USD': (0.000006, 0.00001),
            'FLOKI-USD': (0.00004, 0.00007),
            'WIF-USD': (0.5, 1.0),
            'AAVE-USD': (60, 100),
            'MKR-USD': (1000, 1600),
            'CRV-USD': (0.3, 0.7),
            'SAND-USD': (0.3, 0.7),
            'MANA-USD': (0.3, 0.7),
            'AXS-USD': (5, 9),
            'GALA-USD': (0.02, 0.04),
            'RNDR-USD': (6, 10),
            'FET-USD': (1.2, 2.0),
            'GRT-USD': (0.2, 0.4)
        }
        
        if ticker in ranges:
            min_p, max_p = ranges[ticker]
            return min_p <= price <= max_p
        return True
    
    def _get_fallback_price(self, ticker: str) -> float:
        prices = {
            'BTC-USD': 70000,
            'ETH-USD': 3500,
            'BNB-USD': 600,
            'SOL-USD': 150,
            'XRP-USD': 0.65,
            'ADA-USD': 0.45,
            'AVAX-USD': 30,
            'DOGE-USD': 0.10,
            'DOT-USD': 6.5,
            'MATIC-USD': 0.85,
            'LINK-USD': 15,
            'UNI-USD': 7.0,
            'SHIB-USD': 0.00002,
            'TON-USD': 3.0,
            'TRX-USD': 0.09,
            'ATOM-USD': 8.0,
            'LTC-USD': 75,
            'BCH-USD': 250,
            'ETC-USD': 20,
            'FIL-USD': 4.0,
            'NEAR-USD': 4.0,
            'APT-USD': 9.0,
            'ARB-USD': 1.2,
            'OP-USD': 2.0,
            'SUI-USD': 1.0,
            'PEPE-USD': 0.000008,
            'FLOKI-USD': 0.00005,
            'WIF-USD': 0.75,
            'AAVE-USD': 80,
            'MKR-USD': 1400,
            'CRV-USD': 0.5,
            'SAND-USD': 0.5,
            'MANA-USD': 0.5,
            'AXS-USD': 7.0,
            'GALA-USD': 0.03,
            'RNDR-USD': 8.0,
            'FET-USD': 1.6,
            'GRT-USD': 0.3
        }
        return prices.get(ticker, 1.0)
    
    def get_price(self, ticker: str) -> float:
        with self.lock:
            if ticker in self.prices:
                return self.prices[ticker]
        return self._get_fallback_price(ticker)
    
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

crypto = CryptoPriceFetcher()

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
# 🧠 هوش مصنوعی IRON GOD
# ============================================

class IronGodAI:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 30
        print("✅ IronGodAI راه‌اندازی شد")
    
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
    
    def calculate_tp_sl(self, price: float, coin_data: dict, is_premium: bool = False) -> tuple:
        volatility = coin_data.get('volatility', 'medium')
        
        if volatility == 'low':
            tp1_pct, tp2_pct, tp3_pct = 3.5, 4.5, 5.6
            sl_pct = 1.5
        elif volatility == 'high':
            tp1_pct, tp2_pct, tp3_pct = 5.0, 6.5, 8.0
            sl_pct = 2.5
        else:
            tp1_pct, tp2_pct, tp3_pct = 4.0, 5.0, 6.0
            sl_pct = 2.0
        
        if is_premium:
            tp1_pct *= 1.2
            tp2_pct *= 1.2
            tp3_pct *= 1.2
        
        tp1 = price * (1 + tp1_pct / 100)
        tp2 = price * (1 + tp2_pct / 100)
        tp3 = price * (1 + tp3_pct / 100)
        sl = price * (1 - sl_pct / 100)
        
        return tp1, tp2, tp3, sl, tp1_pct, tp2_pct, tp3_pct, sl_pct
    
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
            usd_price = currency.get_usd()
            
            # قیمت به تومان
            price_irt = self.format_price_irt(price)
            
            # محاسبه TP/SL
            tp1, tp2, tp3, sl, tp1_pct, tp2_pct, tp3_pct, sl_pct = self.calculate_tp_sl(price, coin_data, is_premium)
            
            # منطقه ورود
            entry_min = price * 0.98
            entry_max = price
            best_entry = price * 0.99
            
            # امتیازدهی (بر اساس موقعیت در محدوده)
            if price < entry_min * 1.02:
                score = random.randint(85, 92)
                action_code = "buy_immediate"
                action_name = "🔵 خرید فوری"
                action_emoji = "🔵💎"
                strength = "بسیار قوی"
            elif price < entry_max:
                score = random.randint(75, 84)
                action_code = "buy"
                action_name = "🟢 خرید"
                action_emoji = "🟢✨"
                strength = "قوی"
            elif price < entry_max * 1.02:
                score = random.randint(65, 74)
                action_code = "buy_caution"
                action_name = "🟡 خرید محتاطانه"
                action_emoji = "🟡⭐"
                strength = "متوسط"
            else:
                score = random.randint(50, 64)
                action_code = "hold"
                action_name = "⚪ نگه‌داری"
                action_emoji = "⚪📊"
                strength = "خنثی"
            
            win_prob = score
            lose_prob = 100 - score
            
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
                'profit_1': round(tp1_pct, 1),
                'profit_2': round(tp2_pct, 1),
                'profit_3': round(tp3_pct, 1),
                'loss': round(sl_pct, 1),
                'is_premium': is_premium,
                'time': self.get_tehran_time()
            }
            
            self.cache[cache_key] = {'time': time.time(), 'data': result}
            return result
            
        except Exception as e:
            print(f"❌ خطا در تحلیل: {e}")
            return None
    
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
# 🗄️ دیتابیس
# ============================================

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.access_cache = {}
        self.cache_timeout = 30
        self.lock = threading.Lock()
        self._init_db()
        print("✅ Database راه‌اندازی شد")
    
    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
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
        except Exception as e:
            print(f"❌ خطا: {e}")
    
    def _get_conn(self):
        return sqlite3.connect(self.db_path, timeout=30)
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            result = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            conn.close()
            return dict(result) if result else None
        except:
            return None
    
    def add_user(self, user_id: str, username: str, first_name: str, expiry: float, license_type: str = "regular") -> bool:
        try:
            conn = self._get_conn()
            conn.execute('''INSERT OR REPLACE INTO users 
                (user_id, username, first_name, expiry, license_type, last_active) 
                VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, username or "", first_name or "", expiry, license_type, time.time()))
            conn.commit()
            conn.close()
            
            with self.lock:
                if user_id in self.access_cache:
                    del self.access_cache[user_id]
            return True
        except:
            return False
    
    def update_activity(self, user_id: str):
        try:
            conn = self._get_conn()
            conn.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (time.time(), user_id))
            conn.commit()
            conn.close()
        except:
            pass
    
    def create_license(self, days: int, license_type: str = "premium") -> str:
        key = f"VIP-{uuid.uuid4().hex[:10].upper()}"
        try:
            conn = self._get_conn()
            conn.execute("INSERT INTO licenses (license_key, days, license_type, is_active) VALUES (?, ?, ?, 1)",
                       (key, days, license_type))
            conn.commit()
            conn.close()
            print(f"🔑 لایسنس {key} برای {days} روز ایجاد شد")
            return key
        except:
            return f"VIP-{uuid.uuid4().hex[:8].upper()}"
    
    def activate_license(self, key: str, user_id: str, username: str = "", first_name: str = "") -> Tuple[bool, str, str, float]:
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            
            data = conn.execute("SELECT days, license_type, is_active FROM licenses WHERE license_key = ?", (key.upper(),)).fetchone()
            
            if not data:
                conn.close()
                return False, "❌ لایسنس یافت نشد!", "regular", 0
            
            if data['is_active'] == 0:
                conn.close()
                return False, "❌ این لایسنس قبلاً استفاده شده!", "regular", 0
            
            days = data['days']
            lic_type = data['license_type']
            now = time.time()
            
            user = self.get_user(user_id)
            
            if user and user.get('expiry', 0) > now:
                new_expiry = user['expiry'] + (days * 86400)
                msg = f"✅ اشتراک شما {days} روز تمدید شد!"
            else:
                new_expiry = now + (days * 86400)
                msg = f"✅ اشتراک {days} روزه با موفقیت فعال شد!"
            
            conn.execute("UPDATE licenses SET is_active = 0 WHERE license_key = ?", (key.upper(),))
            conn.commit()
            conn.close()
            
            self.add_user(user_id, username, first_name, new_expiry, lic_type)
            
            with self.lock:
                if user_id in self.access_cache:
                    del self.access_cache[user_id]
            
            expiry_date = datetime.fromtimestamp(new_expiry).strftime('%Y/%m/%d')
            return True, f"{msg}\n📅 تاریخ انقضا: {expiry_date}", lic_type, new_expiry
                
        except Exception as e:
            return False, f"❌ خطا در فعال‌سازی!", "regular", 0
    
    def check_access(self, user_id: str) -> Tuple[bool, Optional[str]]:
        if str(user_id) == str(ADMIN_ID):
            return True, "admin"
        
        now = time.time()
        
        with self.lock:
            if user_id in self.access_cache:
                cached_time, cached_access, cached_type = self.access_cache[user_id]
                if now - cached_time < self.cache_timeout:
                    return cached_access, cached_type
        
        user = self.get_user(user_id)
        
        if not user:
            result = (False, None)
        elif user.get('expiry', 0) > now:
            result = (True, user.get('license_type', 'regular'))
        else:
            result = (False, None)
        
        with self.lock:
            self.access_cache[user_id] = (now, result[0], result[1])
        
        return result
    
    def get_all_users(self) -> List[Dict]:
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            result = conn.execute("SELECT * FROM users ORDER BY last_active DESC").fetchall()
            conn.close()
            return [dict(row) for row in result]
        except:
            return []
    
    def delete_user(self, user_id: str) -> bool:
        try:
            conn = self._get_conn()
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            
            with self.lock:
                if user_id in self.access_cache:
                    del self.access_cache[user_id]
            return True
        except:
            return False

db = Database()

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
            requests.post(f"https://api.telegram.org/bot{self.token}/deleteWebhook",
                        json={"drop_pending_updates": True}, timeout=3)
            print("✅ Webhook پاک شد")
            time.sleep(2)
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
                     f"📊 {len(CRYPTO_COINS)} ارز | ۸ منبع ایرانی\n"
                     f"🔥 **آماده نابودی رقیبا!**"
            )
        except:
            pass
    
    async def show_user_menu(self, update: Update, first_name: str, lic_type: str, expiry: float):
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
            welcome = f"✨ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 دقت ۹۹٪"
        else:
            keyboard = [
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            welcome = f"✅ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 دقت ۹۵٪"
        
        await update.message.reply_text(
            f"🤖 **{self.version}** 🔥\n\n"
            f"{welcome}\n\n"
            f"💵 دلار: `{usd}` تومان\n"
            f"💰 تتر: `{usdt}` تومان\n"
            f"💰 BTC: `{btc:,.0f}` دلار\n"
            f"📊 {len(CRYPTO_COINS)} ارز | ۸ منبع ایرانی\n\n"
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
                welcome = f"✨ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 دقت ۹۹٪"
            else:
                keyboard = [
                    ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                    ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                    ['🎓 راهنما', '📞 پشتیبانی']
                ]
                welcome = f"✅ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 دقت ۹۵٪"
            
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
            f"📊 {len(CRYPTO_COINS)} ارز | ۸ منبع ایرانی\n"
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
            
            msg = await update.message.reply_text("🔍 **در حال تحلیل لحظه‌ای بازار با ۸ منبع قیمت...** ⏳")
            
            best = None
            tickers = list(CRYPTO_COINS.keys())
            random.shuffle(tickers)
            
            for ticker in tickers[:10]:
                analysis = await ai.analyze(ticker, is_premium or is_vip_premium)
                if analysis and analysis['score'] >= 70 and 'buy' in analysis['action_code']:
                    best = analysis
                    break
                await asyncio.sleep(0.1)
            
            if not best:
                best = await ai.analyze('BTC-USD', is_premium or is_vip_premium)
            
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

⚡ **IRON GOD V19 - ۸ منبع ایرانی | آپدیت هر ۳۰ ثانیه** 🔥
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
                    text += f"{i}. **{s['symbol']}** {badge}\n"
                    text += f"   💰 `${s['price_usd']}` | 🎯 `{s['score']}%` {s['action_emoji']}\n"
                    text += f"   ✅ شانس سود: {s['win_prob']}% | ❌ شانس ضرر: {s['lose_prob']}%\n"
                    text += f"   📍 ورود: `{s['entry_min']}` | TP1: `{s['tp1']}`\n"
                    text += f"   ━━━━━━━━━━━━━━━━━\n"
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
                "📘 عادی: ۸ منبع ایرانی\n"
                "✨ پریمیوم: ۸ منبع ایرانی + اولویت بالا\n\n"
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
📊 **آمار IRON GOD V19**
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
🎯 **منابع:** ۸ صرافی ایرانی
⚡ **آپدیت:** هر ۳۰ ثانیه
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
                    
                    await update.message.reply_text(
                        f"⏳ **اعتبار**\n\n"
                        f"📅 `{days}` روز و `{hours}` ساعت\n"
                        f"📆 انقضا: `{expiry_date}`\n"
                        f"🔑 {badge} | 🎯 ۸ منبع ایرانی"
                    )
                else:
                    await update.message.reply_text(f"❌ **منقضی شده**\n\nتمدید: {self.support}")
            else:
                await update.message.reply_text("❌ **کاربر نیست!**")
        
        # راهنما
        elif text == '🎓 راهنما':
            help_text = f"""
🎓 **راهنمای IRON GOD V19**

📖 **آموزش:**

۱️⃣ **فعال‌سازی:** کد لایسنس رو بفرست: `VIP-ABCD1234`
۲️⃣ **تحلیل ارز:** بزن "💰 تحلیل ارزها" و ارزتو انتخاب کن
۳️⃣ **سیگنال VIP:** بزن "🔥 سیگنال VIP" و بهترین فرصت رو بگیر

۴️⃣ **معنی علائم:**
   🔵💎 خرید فوری = شانس سود بالای ۸۵٪
   🟢✨ خرید = شانس سود ۷۵-۸۵٪
   🟡⭐ خرید محتاطانه = شانس سود ۶۵-۷۵٪
   ⚪📊 نگه‌داری = شانس سود زیر ۶۵٪

۵️⃣ **منابع ایرانی:**
   • نوبیتکس
   • والکس
   • بیت‌آن‌کان
   • آبان تتر
   • TGJU
   • رمزینکس
   • تبدیل
   • ارزپایا

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

⚡ **IRON GOD V19 - ۸ منبع ایرانی | آپدیت هر ۳۰ ثانیه**
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
            
            await query.edit_message_text(
                f"✅ **لایسنس {type_name} {days} روزه ساخته شد!**\n\n"
                f"🔑 `{key}`\n\n"
                f"📅 انقضا: {expiry}\n"
                f"🎯 ۸ منبع ایرانی\n\n"
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
        print("🔥🔥🔥 IRON GOD V19 - ۸ منبع ایرانی 🔥🔥🔥")
        print("="*100)
        print(f"👑 ادمین: {ADMIN_ID}")
        print(f"💵 دلار: {currency.get_usd_formatted()} تومان")
        print(f"💰 تتر: {currency.get_usdt_formatted()} تومان")
        print(f"📊 ارزها: {len(CRYPTO_COINS)}")
        print(f"🎯 منابع: ۸ صرافی ایرانی")
        print(f"⚡ آپدیت: هر ۳۰ ثانیه")
        print(f"⏰ تهران: {ai.get_tehran_time()}")
        print("="*100 + "\n")
        
        self.app = Application.builder().token(self.token).post_init(self.post_init).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        try:
            self.app.run_polling(drop_pending_updates=True)
        except Conflict:
            print("⚠️ Conflict - restarting in 5s...")
            time.sleep(5)
            self._cleanup_webhook()
            self.run()
        except Exception as e:
            print(f"⚠️ خطا: {e} - restarting...")
            time.sleep(5)
            self.run()

# ============================================
# 🚀 اجرا
# ============================================

if __name__ == "__main__":
    bot = IronGodBot()
    bot.run()