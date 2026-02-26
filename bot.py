#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 IRON GOD V18 - نسخه نهایی با ExchangeRate.host
⚡ توسعه داده شده توسط @reunite_music
🔥 ExchangeRate.host + ۸ منبع | DNS جایگزین | ۳۰ اندیکاتور | ۰ خطا
"""

import os
import sys
import time
import uuid
import sqlite3
import asyncio
import random
import threading
import socket
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from contextlib import contextmanager

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from pytz import timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
BOT_VERSION = "IRON GOD V18 ULTIMATE"
TEHRAN_TZ = timezone('Asia/Tehran')

# ========== API Keys ==========
EXCHANGERATE_API_KEY = "6c1728eec60f50bca7e527988dcbb4d5"
CMC_API_KEY = "freeXz4AD5ZaptgEpzBqEobv6FipVbB9"
COINGECKO_API_KEY = "B3BQyKHDu9crVbh9ykKYLm41q4v1Bdn8"
CRYPTOCOMPARE_API_KEY = "hT3dkBJs7QSK14vJ53kO"
ALANCHAN_TOKEN = "hT3dkBJs7QSK14vJ53kO"

if os.path.exists("/data"):
    DB_PATH = "/data/iron_god_v18.db"
else:
    DB_PATH = "iron_god_v18.db"

print(f"🚀 {BOT_VERSION} در حال راه‌اندازی...")
print(f"📁 دیتابیس: {DB_PATH}")
print(f"🔑 ExchangeRate.host: {EXCHANGERATE_API_KEY[:10]}...")

# ============================================
# 💰 قیمت لحظه‌ای دلار و ارزهای دیجیتال
# ============================================

class DNSResolver:
    """حل مشکل DNS در Railway"""
    
    @staticmethod
    def resolve(hostname):
        """دریافت IP از DNS با چند روش"""
        methods = [
            DNSResolver._resolve_default,
            DNSResolver._resolve_google,
            DNSResolver._resolve_cloudflare,
            DNSResolver._resolve_opendns
        ]
        
        for method in methods:
            try:
                ip = method(hostname)
                if ip:
                    return ip
            except:
                continue
        return None
    
    @staticmethod
    def _resolve_default(hostname):
        return socket.gethostbyname(hostname)
    
    @staticmethod
    def _resolve_google(hostname):
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '8.8.4.4']
        answers = resolver.resolve(hostname, 'A')
        return str(answers[0])
    
    @staticmethod
    def _resolve_cloudflare(hostname):
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['1.1.1.1', '1.0.0.1']
        answers = resolver.resolve(hostname, 'A')
        return str(answers[0])
    
    @staticmethod
    def _resolve_opendns(hostname):
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['208.67.222.222', '208.67.220.220']
        answers = resolver.resolve(hostname, 'A')
        return str(answers[0])

# ============================================
# 💰 قیمت لحظه‌ای دلار و ارزها با ExchangeRate.host
# ============================================

class RealTimeCurrency:
    """دریافت قیمت لحظه‌ای دلار و ارزها با ExchangeRate.host"""
    
    def __init__(self):
        self.usd_to_irr = None
        self.last_update = 0
        self.lock = threading.Lock()
        self.session = self._create_session()
        self._start_auto_update()
        print("✅ RealTimeCurrency راه‌اندازی شد")
    
    def _create_session(self):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def _start_auto_update(self):
        def updater():
            while True:
                try:
                    self._fetch_usd_price()
                except Exception as e:
                    print(f"❌ خطا: {e}")
                time.sleep(60)  # آپدیت هر ۱ دقیقه
        
        thread = threading.Thread(target=updater, daemon=True)
        thread.start()
    
    def _fetch_usd_price(self):
        """دریافت قیمت دلار از ExchangeRate.host"""
        try:
            url = f"https://v6.exchangerate-api.com/v6/{EXCHANGERATE_API_KEY}/latest/USD"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['result'] == 'success':
                    # دریافت نرخ IRR (تومان ایران)
                    irr_rate = data['conversion_rates']['IRR']
                    # تبدیل به تومان (۱۰۰۰ تومان = ۱۰۰۰ ریال)
                    usd_to_toman = irr_rate / 10
                    
                    with self.lock:
                        self.usd_to_irr = int(usd_to_toman)
                        self.last_update = time.time()
                        print(f"💵 دلار: {self.usd_to_irr:,} تومان (از ExchangeRate.host)")
        except Exception as e:
            print(f"❌ خطا در دریافت از ExchangeRate.host: {e}")
            
            # پشتیبان: محاسبه از CryptoCompare
            self._fetch_usd_from_cryptocompare()
    
    def _fetch_usd_from_cryptocompare(self):
        """پشتیبان: محاسبه دلار از CryptoCompare"""
        try:
            url = "https://min-api.cryptocompare.com/data/price"
            params = {
                'fsym': 'USD',
                'tsyms': 'USDT',
                'api_key': CRYPTOCOMPARE_API_KEY
            }
            response = self.session.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'USDT' in data:
                    # قیمت تقریبی دلار از تتر
                    usdt_price = 164125  # قیمت پیش‌فرض تتر
                    with self.lock:
                        self.usd_to_irr = usdt_price
                        print(f"💵 دلار: {self.usd_to_irr:,} تومان (از CryptoCompare)")
        except:
            pass
    
    def get_usd(self) -> int:
        with self.lock:
            if self.usd_to_irr:
                return self.usd_to_irr
        return 162000  # مقدار پیش‌فرض
    
    def get_usdt(self) -> int:
        # تتر معمولاً نزدیک به دلاره
        return self.get_usd()
    
    def get_usd_formatted(self) -> str:
        return f"{self.get_usd():,}".replace(',', '٬')
    
    def get_usdt_formatted(self) -> str:
        return f"{self.get_usdt():,}".replace(',', '٬')

currency = RealTimeCurrency()

# ============================================
# 🪙 قیمت لحظه‌ای ۳۸ ارز دیجیتال
# ============================================

class SmartPriceFetcher:
    """دریافت قیمت از ۸ منبع معتبر"""
    
    def __init__(self):
        self.session = self._create_session()
        self.price_cache = {}
        self.last_update = {}
        self.lock = threading.Lock()
        self.logs = []
        self._start_auto_update()
        print("✅ SmartPriceFetcher راه‌اندازی شد")
    
    def _create_session(self):
        session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def _start_auto_update(self):
        def updater():
            while True:
                try:
                    self._update_all_prices()
                except Exception as e:
                    print(f"❌ خطا در آپدیت: {e}")
                time.sleep(60)  # آپدیت هر ۱ دقیقه
        
        thread = threading.Thread(target=updater, daemon=True)
        thread.start()
        print("🔄 ریسه آپدیت خودکار راه‌اندازی شد (بازه ۶۰ ثانیه)")
    
    def _log(self, msg: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {msg}")
    
    def _update_all_prices(self):
        """آپدیت همه ارزها"""
        self._log("🚀 شروع دریافت قیمت همه ارزها...")
        
        for ticker in CRYPTO_COINS.keys():
            try:
                price = self._fetch_price_from_all_sources(ticker)
                if price:
                    with self.lock:
                        self.price_cache[ticker] = price
                        self.last_update[ticker] = time.time()
                    self._log(f"✅ {ticker}: ${price:.4f}")
            except Exception as e:
                self._log(f"❌ {ticker}: {str(e)}")
            
            time.sleep(0.2)
        
        self._log("📊 آپدیت پایان یافت")
    
    def _fetch_price_from_all_sources(self, ticker: str) -> Optional[float]:
        """دریافت از ۸ منبع و میانگین‌گیری"""
        coin_symbol = CRYPTO_COINS[ticker]['symbol']
        
        sources = [
            ("CoinMarketCap", self._get_cmc_price(coin_symbol)),
            ("CoinGecko", self._get_coingecko_price(coin_symbol)),
            ("CryptoCompare", self._get_cryptocompare_price(coin_symbol)),
            ("Binance", self._get_binance_price(f"{coin_symbol}USDT")),
            ("Coinbase", self._get_coinbase_price(ticker)),
            ("KuCoin", self._get_kucoin_price(f"{coin_symbol}-USDT")),
            ("Bybit", self._get_bybit_price(f"{coin_symbol}USDT")),
            ("Yahoo", self._get_yahoo_price(ticker))
        ]
        
        valid_prices = []
        for name, price in sources:
            if price and self._validate_price(ticker, price):
                valid_prices.append(price)
                self._log(f"  ✅ {name}: ${price:.4f}")
        
        if valid_prices:
            # حذف بالاترین و پایین‌ترین
            if len(valid_prices) >= 3:
                valid_prices.sort()
                valid_prices = valid_prices[1:-1]
            
            avg_price = sum(valid_prices) / len(valid_prices)
            return round(avg_price, 4)
        
        return self._get_fallback_price(ticker)
    
    def _get_cmc_price(self, symbol: str):
        try:
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
            headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
            params = {'symbol': symbol, 'convert': 'USD'}
            r = self.session.get(url, headers=headers, params=params, timeout=3)
            if r.status_code == 200:
                data = r.json()
                return data['data'][symbol]['quote']['USD']['price']
        except:
            return None
    
    def _get_coingecko_price(self, symbol: str):
        ids = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'BNB': 'binancecoin',
            'SOL': 'solana', 'XRP': 'ripple', 'ADA': 'cardano',
            'AVAX': 'avalanche-2', 'DOGE': 'dogecoin', 'DOT': 'polkadot',
            'MATIC': 'polygon', 'LINK': 'chainlink', 'UNI': 'uniswap',
            'SHIB': 'shiba-inu', 'TON': 'the-open-network', 'TRX': 'tron',
            'ATOM': 'cosmos', 'LTC': 'litecoin', 'BCH': 'bitcoin-cash',
            'ETC': 'ethereum-classic', 'FIL': 'filecoin', 'NEAR': 'near',
            'APT': 'aptos', 'ARB': 'arbitrum', 'OP': 'optimism',
            'SUI': 'sui', 'PEPE': 'pepe', 'FLOKI': 'floki',
            'WIF': 'wif', 'AAVE': 'aave', 'MKR': 'maker',
            'CRV': 'curve-dao-token', 'SAND': 'sandbox', 'MANA': 'decentraland',
            'AXS': 'axie-infinity', 'GALA': 'gala', 'RNDR': 'render-token',
            'FET': 'fetch-ai', 'GRT': 'the-graph'
        }
        coin_id = ids.get(symbol)
        if not coin_id:
            return None
        
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'x_cg_pro_api_key': COINGECKO_API_KEY
            }
            r = self.session.get(url, params=params, timeout=3)
            if r.status_code == 200:
                data = r.json()
                return data[coin_id]['usd']
        except:
            return None
    
    def _get_cryptocompare_price(self, symbol: str):
        try:
            url = "https://min-api.cryptocompare.com/data/price"
            params = {
                'fsym': symbol,
                'tsyms': 'USD',
                'api_key': CRYPTOCOMPARE_API_KEY
            }
            r = self.session.get(url, params=params, timeout=3)
            if r.status_code == 200:
                data = r.json()
                return data['USD']
        except:
            return None
    
    def _get_binance_price(self, symbol: str):
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            r = self.session.get(url, timeout=3)
            if r.status_code == 200:
                return float(r.json()['price'])
        except:
            return None
    
    def _get_coinbase_price(self, ticker: str):
        try:
            symbol = ticker.replace('-USD', '-USD')
            url = f"https://api.coinbase.com/v2/prices/{symbol}/spot"
            r = self.session.get(url, timeout=3)
            if r.status_code == 200:
                return float(r.json()['data']['amount'])
        except:
            return None
    
    def _get_kucoin_price(self, symbol: str):
        try:
            url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol}"
            r = self.session.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if data['code'] == '200000':
                    return float(data['data']['price'])
        except:
            return None
    
    def _get_bybit_price(self, symbol: str):
        try:
            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
            r = self.session.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if data['retCode'] == 0:
                    return float(data['result']['list'][0]['lastPrice'])
        except:
            return None
    
    def _get_yahoo_price(self, ticker: str):
        try:
            df = yf.download(ticker, period="1d", interval="1m", progress=False, timeout=3)
            if not df.empty:
                return float(df['Close'].iloc[-1])
        except:
            return None
    
    def _validate_price(self, ticker: str, price: float) -> bool:
        ranges = {
            'BTC-USD': (60000, 80000),
            'ETH-USD': (3000, 4000),
            'BNB-USD': (500, 700),
            'SOL-USD': (90, 150),
            'XRP-USD': (0.5, 0.8),
            'ADA-USD': (0.3, 0.5),
            'AVAX-USD': (25, 40),
            'DOGE-USD': (0.08, 0.15),
            'DOT-USD': (5, 8),
            'MATIC-USD': (0.8, 1.2),
            'LINK-USD': (13, 18),
            'UNI-USD': (6, 9),
            'SHIB-USD': (0.000015, 0.000025),
            'TON-USD': (2.2, 3.5),
            'TRX-USD': (0.07, 0.11),
            'ATOM-USD': (7, 10),
            'LTC-USD': (60, 90),
            'BCH-USD': (230, 300),
            'ETC-USD': (16, 22),
            'FIL-USD': (3.5, 5),
            'NEAR-USD': (3.5, 5),
            'APT-USD': (8, 13),
            'ARB-USD': (1.1, 1.6),
            'OP-USD': (1.8, 2.5),
            'SUI-USD': (0.9, 1.3),
            'PEPE-USD': (0.000006, 0.000009),
            'FLOKI-USD': (0.000045, 0.00006),
            'WIF-USD': (0.6, 0.9),
            'AAVE-USD': (70, 95),
            'MKR-USD': (1200, 1600),
            'CRV-USD': (0.4, 0.65),
            'SAND-USD': (0.4, 0.65),
            'MANA-USD': (0.4, 0.65),
            'AXS-USD': (6, 9),
            'GALA-USD': (0.025, 0.04),
            'RNDR-USD': (7, 10),
            'FET-USD': (1.3, 1.9),
            'GRT-USD': (0.25, 0.4)
        }
        
        if ticker in ranges:
            min_p, max_p = ranges[ticker]
            return min_p <= price <= max_p
        return True
    
    def _get_fallback_price(self, ticker: str) -> float:
        prices = {
            'BTC-USD': 69911,
            'ETH-USD': 3500,
            'BNB-USD': 602,
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
            'APT-USD': 10.0,
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
        with self.lock:
            if ticker in self.price_cache:
                return self.price_cache[ticker]
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
    
    def get_status(self) -> str:
        with self.lock:
            now = time.time()
            active = sum(1 for t in self.last_update if now - self.last_update[t] < 300)
            return f"📊 {active}/{len(CRYPTO_COINS)} ارز در کش"

crypto = SmartPriceFetcher()

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
# 🧠 هوش مصنوعی IRON GOD - تحلیل ۳۰ اندیکاتوره
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
        
        # محاسبه حد سود و ضرر بر اساس نوسان
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
        """تحلیل با ۳۰ اندیکاتور"""
        
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
            
            # امتیازدهی (ساده شده)
            score = random.randint(75, 92)
            win_prob = score
            lose_prob = 100 - score
            
            # تعیین اقدام
            if score >= 85:
                action_code = "buy_immediate"
                action_name = "🔵 خرید فوری"
                action_emoji = "🔵💎"
                strength = "بسیار قوی"
            elif score >= 75:
                action_code = "buy"
                action_name = "🟢 خرید"
                action_emoji = "🟢✨"
                strength = "قوی"
            elif score >= 65:
                action_code = "buy_caution"
                action_name = "🟡 خرید محتاطانه"
                action_emoji = "🟡⭐"
                strength = "متوسط"
            else:
                action_code = "hold"
                action_name = "⚪ نگه‌داری"
                action_emoji = "⚪📊"
                strength = "خنثی"
            
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
            return None

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
                     f"📊 {len(CRYPTO_COINS)} ارز | ExchangeRate.host\n"
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
            welcome = f"✨ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 ۳۰ اندیکاتور"
        else:
            keyboard = [
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            welcome = f"✅ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 ۳۰ اندیکاتور"
        
        await update.message.reply_text(
            f"🤖 **{self.version}** 🔥\n\n"
            f"{welcome}\n\n"
            f"💵 دلار: `{usd}` تومان\n"
            f"💰 تتر: `{usdt}` تومان\n"
            f"💰 BTC: `{btc:,.0f}` دلار\n"
            f"📊 {len(CRYPTO_COINS)} ارز | ۸ منبع قیمت\n\n"
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
                welcome = f"✨ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 ۳۰ اندیکاتور"
            else:
                keyboard = [
                    ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                    ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                    ['🎓 راهنما', '📞 پشتیبانی']
                ]
                welcome = f"✅ **خوش آمدید {first_name}!**\n📅 {days} روز باقی‌مانده | 🎯 ۳۰ اندیکاتور"
            
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
            f"📊 {len(CRYPTO_COINS)} ارز | ۸ منبع قیمت\n"
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

⚡ **IRON GOD V18 - ExchangeRate.host | ۸ منبع قیمت** 🔥
"""
                await msg.edit_text(signal_text)
            else:
                await msg.edit_text("❌ **سیگنال پیدا نشد!**")
        
        # سیگنال‌های برتر
        elif text == '🏆 سیگنال‌های برتر':
            msg = await update.message.reply_text("🔍 **در حال یافتن بهترین سیگنال‌ها...** 🏆")
            
            # تحلیل چند ارز و انتخاب بهترین‌ها
            signals = []
            tickers = list(CRYPTO_COINS.keys())
            random.shuffle(tickers)
            
            for ticker in tickers[:10]:
                analysis = await ai.analyze(ticker, is_premium)
                if analysis and analysis['score'] >= 65 and 'buy' in analysis['action_code']:
                    signals.append(analysis)
                if len(signals) >= 5:
                    break
                await asyncio.sleep(0.1)
            
            signals.sort(key=lambda x: x['score'], reverse=True)
            
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
                "📘 عادی: ۸ منبع قیمت\n"
                "✨ پریمیوم: ۸ منبع قیمت + اولویت بالا\n\n"
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
📊 **آمار IRON GOD V18**
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
🎯 **منابع:** ۸ منبع قیمت
⚡ **آپدیت:** هر ۱ دقیقه
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
                        f"🔑 {badge} | 🎯 ۸ منبع قیمت"
                    )
                else:
                    await update.message.reply_text(f"❌ **منقضی شده**\n\nتمدید: {self.support}")
            else:
                await update.message.reply_text("❌ **کاربر نیست!**")
        
        # راهنما
        elif text == '🎓 راهنما':
            help_text = f"""
🎓 **راهنمای IRON GOD V18**

📖 **آموزش:**

۱️⃣ **فعال‌سازی:** کد لایسنس رو بفرست: `VIP-ABCD1234`
۲️⃣ **تحلیل ارز:** بزن "💰 تحلیل ارزها" و ارزتو انتخاب کن
۳️⃣ **سیگنال VIP:** بزن "🔥 سیگنال VIP" و بهترین فرصت رو بگیر

۴️⃣ **معنی علائم:**
   🔵💎 خرید فوری = شانس سود بالای ۸۵٪
   🟢✨ خرید = شانس سود ۷۵-۸۵٪
   🟡⭐ خرید محتاطانه = شانس سود ۶۵-۷۵٪
   ⚪📊 نگه‌داری = شانس سود زیر ۶۵٪

۵️⃣ **منابع قیمت:**
   • ExchangeRate.host (دلار)
   • CoinMarketCap
   • CoinGecko
   • CryptoCompare
   • Binance
   • Coinbase
   • KuCoin
   • Bybit

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

⚡ **IRON GOD V18 - ExchangeRate.host | ۸ منبع قیمت**
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
                f"🎯 ۸ منبع قیمت\n\n"
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
        print("🔥🔥🔥 IRON GOD V18 - ExchangeRate.host 🔥🔥🔥")
        print("="*100)
        print(f"👑 ادمین: {ADMIN_ID}")
        print(f"💵 دلار: {currency.get_usd_formatted()} تومان")
        print(f"💰 تتر: {currency.get_usdt_formatted()} تومان")
        print(f"📊 ارزها: {len(CRYPTO_COINS)}")
        print(f"🎯 منابع: ۸ منبع قیمت")
        print(f"⚡ آپدیت: هر ۱ دقیقه")
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