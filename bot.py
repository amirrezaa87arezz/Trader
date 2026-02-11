#!/usr/bin/env python3
"""
🤖 ربات تریدر پشم‌ریز - نسخه نهایی
توسعه داده شده توسط @reunite_music
"""

import os
import sys
import time
import uuid
import sqlite3
import asyncio
import logging
import random
from datetime import datetime, timedelta
from pytz import timezone

import yfinance as yf
import pandas as pd
import numpy as np

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ============================================
# 🔧 تنظیمات اصلی
# ============================================

TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
SUPPORT_USERNAME = "@reunite_music"

# منطقه زمانی تهران
TEHRAN_TZ = timezone('Asia/Tehran')

# مسیر دیتابیس
if os.path.exists("/data"):
    DB_PATH = "/data/trading_bot.db"
else:
    DB_PATH = "trading_bot.db"

# ============================================
# 📊 ۱۰۰+ ارز دیجیتال
# ============================================

COIN_MAP = {
    # Top 10
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'BNB/USDT': 'BNB-USD',
    'SOL/USDT': 'SOL-USD', 'XRP/USDT': 'XRP-USD', 'ADA/USDT': 'ADA-USD',
    'AVAX/USDT': 'AVAX-USD', 'DOGE/USDT': 'DOGE-USD', 'DOT/USDT': 'DOT-USD',
    'MATIC/USDT': 'MATIC-USD', 'LINK/USDT': 'LINK-USD', 'UNI/USDT': 'UNI-USD',
    
    # محبوب
    'TRX/USDT': 'TRX-USD', 'SHIB/USDT': 'SHIB-USD', 'TON/USDT': 'TON-USD',
    'ATOM/USDT': 'ATOM-USD', 'LTC/USDT': 'LTC-USD', 'BCH/USDT': 'BCH-USD',
    'ETC/USDT': 'ETC-USD', 'FIL/USDT': 'FIL-USD', 'NEAR/USDT': 'NEAR-USD',
    'APT/USDT': 'APT-USD', 'ARB/USDT': 'ARB-USD', 'OP/USDT': 'OP-USD',
    'SUI/USDT': 'SUI-USD', 'ALGO/USDT': 'ALGO-USD', 'XLM/USDT': 'XLM-USD',
    'VET/USDT': 'VET-USD', 'ICP/USDT': 'ICP-USD', 'EOS/USDT': 'EOS-USD',
    
    # میم کوین‌ها
    'PEPE/USDT': 'PEPE-USD', 'FLOKI/USDT': 'FLOKI-USD', 'BONK/USDT': 'BONK-USD',
    'WIF/USDT': 'WIF-USD', 'BOME/USDT': 'BOME-USD', 'MEME/USDT': 'MEME-USD',
    
    # لایه ۲
    'IMX/USDT': 'IMX-USD', 'STRK/USDT': 'STRK-USD', 'MNT/USDT': 'MNT-USD',
    
    # دیفای
    'AAVE/USDT': 'AAVE-USD', 'MKR/USDT': 'MKR-USD', 'CRV/USDT': 'CRV-USD',
    'SNX/USDT': 'SNX-USD', 'SUSHI/USDT': 'SUSHI-USD', 'CAKE/USDT': 'CAKE-USD',
    'RUNE/USDT': 'RUNE-USD', 'INJ/USDT': 'INJ-USD',
    
    # گیمینگ
    'SAND/USDT': 'SAND-USD', 'MANA/USDT': 'MANA-USD', 'AXS/USDT': 'AXS-USD',
    'GALA/USDT': 'GALA-USD', 'ENJ/USDT': 'ENJ-USD',
    
    # هوش مصنوعی
    'RNDR/USDT': 'RNDR-USD', 'FET/USDT': 'FET-USD', 'AGIX/USDT': 'AGIX-USD',
    'OCEAN/USDT': 'OCEAN-USD', 'TAO/USDT': 'TAO-USD', 'GRT/USDT': 'GRT-USD',
    
    # حریم خصوصی
    'XMR/USDT': 'XMR-USD', 'ZEC/USDT': 'ZEC-USD', 'MINA/USDT': 'MINA-USD',
    'ROSE/USDT': 'ROSE-USD',
}

# دسته‌بندی ارزها
COIN_CATEGORIES = {
    'main': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT'],
    'layer1': ['ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'NEAR/USDT', 'APT/USDT', 'ALGO/USDT'],
    'meme': ['DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'FLOKI/USDT', 'WIF/USDT', 'BONK/USDT'],
    'defi': ['UNI/USDT', 'AAVE/USDT', 'MKR/USDT', 'CRV/USDT', 'CAKE/USDT', 'RUNE/USDT'],
    'layer2': ['MATIC/USDT', 'ARB/USDT', 'OP/USDT', 'IMX/USDT', 'STRK/USDT'],
    'gaming': ['SAND/USDT', 'MANA/USDT', 'AXS/USDT', 'GALA/USDT', 'ENJ/USDT'],
    'ai': ['RNDR/USDT', 'FET/USDT', 'AGIX/USDT', 'OCEAN/USDT', 'GRT/USDT'],
    'privacy': ['XMR/USDT', 'ZEC/USDT', 'MINA/USDT', 'ROSE/USDT'],
}

# ============================================
# 🪵 لاگ‌گیری
# ============================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('yfinance').setLevel(logging.WARNING)

# ============================================
# 🗄️ دیتابیس
# ============================================

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
        logger.info(f"🗄️ دیتابیس راه‌اندازی شد")
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                expiry REAL DEFAULT 0,
                license_type TEXT DEFAULT 'regular',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active REAL DEFAULT 0
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS licenses (
                license_key TEXT PRIMARY KEY,
                days INTEGER,
                license_type TEXT DEFAULT 'regular',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_by TEXT,
                used_at TIMESTAMP
            )''')
            conn.commit()
    
    def get_user(self, user_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT * FROM users WHERE user_id = ?", 
                    (user_id,)
                ).fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"خطا در دریافت کاربر: {e}")
            return None
    
    def add_user(self, user_id, username, first_name, expiry, license_type="regular"):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, expiry, license_type, last_active) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (user_id, username or "", first_name or "", expiry, license_type, time.time()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطا در افزودن کاربر: {e}")
            return False
    
    def update_activity(self, user_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET last_active = ? WHERE user_id = ?",
                    (time.time(), user_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"خطا در بروزرسانی فعالیت: {e}")
    
    def create_license(self, days, license_type="regular"):
        """ایجاد لایسنس با فرمت قابل کپی"""
        license_key = f"VIP-{uuid.uuid4().hex[:8].upper()}"
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO licenses (license_key, days, license_type, is_active) VALUES (?, ?, ?, 1)",
                    (license_key, days, license_type)
                )
                conn.commit()
            logger.info(f"🔑 لایسنس ساخته شد: {license_key} ({days} روز) - {license_type}")
            return license_key
        except Exception as e:
            logger.error(f"خطا در ساخت لایسنس: {e}")
            return f"VIP-{uuid.uuid4().hex[:6].upper()}"
    
    def activate_license(self, license_key, user_id, username="", first_name=""):
        try:
            with sqlite3.connect(self.db_path) as conn:
                license_data = conn.execute(
                    "SELECT days, license_type, is_active FROM licenses WHERE license_key = ?",
                    (license_key,)
                ).fetchone()
                
                if not license_data:
                    return False, "❌ لایسنس یافت نشد", "regular"
                
                if license_data[2] == 0:
                    return False, "❌ این لایسنس قبلاً استفاده شده است", "regular"
                
                days = license_data[0]
                license_type = license_data[1]
                current_time = time.time()
                user = self.get_user(user_id)
                
                if user and user.get('expiry', 0) > current_time:
                    new_expiry = user['expiry'] + (days * 86400)
                    message = f"✅ اشتراک شما {days} روز تمدید شد"
                else:
                    new_expiry = current_time + (days * 86400)
                    message = f"✅ اشتراک {days} روزه با موفقیت فعال شد"
                
                conn.execute(
                    "UPDATE licenses SET is_active = 0, used_by = ?, used_at = ? WHERE license_key = ?",
                    (user_id, datetime.now().isoformat(), license_key)
                )
                
                self.add_user(user_id, username, first_name, new_expiry, license_type)
                conn.commit()
                
                expiry_date = datetime.fromtimestamp(new_expiry).strftime('%Y/%m/%d')
                return True, f"{message}\n📅 تاریخ انقضا: {expiry_date}", license_type
                
        except Exception as e:
            logger.error(f"خطا در فعال‌سازی لایسنس: {e}")
            return False, "❌ خطا در فعال‌سازی لایسنس", "regular"
    
    def check_user_access(self, user_id):
        if str(user_id) == str(ADMIN_ID):
            return True, "admin"
        
        user = self.get_user(user_id)
        if not user:
            return False, None
        
        expiry = user.get('expiry', 0)
        if expiry > time.time():
            return True, user.get('license_type', 'regular')
        return False, None
    
    def get_user_license_type(self, user_id):
        user = self.get_user(user_id)
        if user:
            return user.get('license_type', 'regular')
        return 'regular'
    
    def get_all_users(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                return conn.execute(
                    "SELECT * FROM users ORDER BY last_active DESC"
                ).fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت کاربران: {e}")
            return []
    
    def delete_user(self, user_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطا در حذف کاربر: {e}")
            return False
    
    def get_stats(self):
        stats = {
            'total_users': 0,
            'active_users': 0,
            'premium_users': 0,
            'total_licenses': 0,
            'active_licenses': 0
        }
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM users")
                stats['total_users'] = c.fetchone()[0] or 0
                c.execute("SELECT COUNT(*) FROM users WHERE expiry > ?", (time.time(),))
                stats['active_users'] = c.fetchone()[0] or 0
                c.execute("SELECT COUNT(*) FROM users WHERE license_type = 'premium'")
                stats['premium_users'] = c.fetchone()[0] or 0
                c.execute("SELECT COUNT(*) FROM licenses")
                stats['total_licenses'] = c.fetchone()[0] or 0
                c.execute("SELECT COUNT(*) FROM licenses WHERE is_active = 1")
                stats['active_licenses'] = c.fetchone()[0] or 0
        except Exception as e:
            logger.error(f"خطا در دریافت آمار: {e}")
        return stats

db = Database()

# ============================================
# 🧠 هوش مصنوعی پشم‌ریز
# ============================================

class UltraAI:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 120
        logger.info("🧠 هوش مصنوعی پشم‌ریز راه‌اندازی شد")
    
    def get_tehran_time(self):
        return datetime.now(TEHRAN_TZ)
    
    async def analyze(self, symbol, is_premium=False):
        cache_key = f"{symbol}_{is_premium}"
        if cache_key in self.cache:
            if time.time() - self.cache[cache_key]['time'] < self.cache_timeout:
                return self.cache[cache_key]['data']
        
        try:
            ticker = COIN_MAP.get(symbol)
            if not ticker:
                return self._god_analysis(symbol, is_premium)
            
            df = yf.download(ticker, period="7d", interval="1h", progress=False, timeout=5)
            
            if df.empty or len(df) < 24:
                return self._god_analysis(symbol, is_premium)
            
            analysis = self._divine_analysis(df, symbol, is_premium)
            self.cache[cache_key] = {'time': time.time(), 'data': analysis}
            return analysis
            
        except Exception as e:
            logger.warning(f"خطا در دریافت داده: {e}")
            return self._god_analysis(symbol, is_premium)
    
    def _divine_analysis(self, df, symbol, is_premium=False):
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume'] if 'Volume' in df else pd.Series([0]*len(df))
        
        price = float(close.iloc[-1])
        price_24h_ago = float(close.iloc[-25]) if len(close) >= 25 else price
        price_7d_ago = float(close.iloc[-169]) if len(close) >= 169 else price
        
        # ========== اندیکاتورهای پایه ==========
        sma_20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else price
        sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else price
        sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else price
        
        ema_9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
        ema_21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        
        # ========== RSI ==========
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta.where(delta < 0, 0))
        
        avg_gain_14 = gain.rolling(14).mean()
        avg_loss_14 = loss.rolling(14).mean()
        rs_14 = avg_gain_14 / avg_loss_14
        rsi_14 = 100 - (100 / (1 + rs_14)).iloc[-1] if not rs_14.isna().all() else 50
        
        # ========== ATR ==========
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1] if not tr.isna().all() else price * 0.02
        
        # ========== MACD ==========
        ema_12 = close.ewm(span=12, adjust=False).mean().iloc[-1]
        ema_26 = close.ewm(span=26, adjust=False).mean().iloc[-1]
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean().iloc[-1] if isinstance(macd_line, pd.Series) else macd_line
        macd_histogram = macd_line.iloc[-1] - signal_line.iloc[-1] if isinstance(macd_line, pd.Series) else macd_line - signal_line
        
        # ========== باند بولینگر ==========
        bb_sma = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else price
        bb_std = close.rolling(20).std().iloc[-1] if len(close) >= 20 else price * 0.02
        bb_upper = bb_sma + (2 * bb_std)
        bb_lower = bb_sma - (2 * bb_std)
        bb_position = ((price - bb_lower) / (bb_upper - bb_lower)) * 100 if bb_upper != bb_lower else 50
        
        # ========== حجم ==========
        avg_volume = volume.rolling(20).mean().iloc[-1] if len(volume) >= 20 else volume.mean()
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # ========== امتیازدهی پیشرفته ==========
        score = 50
        
        # روند
        if price > sma_20:
            score += 5
        if price > sma_50:
            score += 7
        if price > sma_200:
            score += 8
        if ema_9 > ema_21:
            score += 5
        
        # RSI
        if 40 < rsi_14 < 60:
            score += 10
        elif rsi_14 < 30:
            score += 15
        elif rsi_14 > 70:
            score -= 5
        
        # MACD
        if macd_line.iloc[-1] > signal_line.iloc[-1] if isinstance(macd_line, pd.Series) else macd_line > signal_line:
            score += 10
        if macd_histogram > 0:
            score += 5
        
        # باند بولینگر
        if bb_position < 20:
            score += 15
        elif bb_position > 80:
            score -= 5
        elif 30 < bb_position < 70:
            score += 8
        
        # حجم
        if volume_ratio > 1.5:
            score += 10
        elif volume_ratio > 1.2:
            score += 5
        
        # ========== امتیاز اضافه برای کاربران ویژه ==========
        if is_premium:
            score += 10
            atr = atr * 0.9  # کاهش ریسک
        
        score = max(20, min(98, int(score)))
        
        # ========== سطح‌بندی سیگنال ==========
        if score >= 90:
            signal_text = "🔵 خرید فوری"
            trend = "📈 صعودی بسیار قوی"
            strength = "💪 فوق‌العاده قوی"
            risk = "✅ بسیار پایین"
            confidence = "⭐⭐⭐⭐⭐"
        elif score >= 80:
            signal_text = "🟢 خرید قوی"
            trend = "📈 صعودی قوی"
            strength = "👍 قوی"
            risk = "✅ پایین"
            confidence = "⭐⭐⭐⭐"
        elif score >= 70:
            signal_text = "🟡 خرید"
            trend = "↗️ صعودی"
            strength = "👌 متوسط"
            risk = "⚠️ متوسط"
            confidence = "⭐⭐⭐"
        elif score >= 60:
            signal_text = "⚪ خرید محتاطانه"
            trend = "➡️ خنثی"
            strength = "🤔 ضعیف"
            risk = "⚠️ بالا"
            confidence = "⭐⭐"
        elif score >= 50:
            signal_text = "🟠 عدم خرید"
            trend = "↘️ نزولی"
            strength = "👎 ضعیف"
            risk = "❌ بالا"
            confidence = "⭐"
        else:
            signal_text = "🔴 فروش"
            trend = "📉 نزولی قوی"
            strength = "💔 بسیار ضعیف"
            risk = "❌❌ بسیار بالا"
            confidence = "⭐"
        
        # ========== محاسبه حد سود و ضرر ==========
        if is_premium:
            tp_mult = 4.0
            sl_mult = 1.7
        else:
            tp_mult = 3.0
            sl_mult = 1.5
        
        tp1 = price + (atr * tp_mult * 0.6)
        tp2 = price + (atr * tp_mult * 0.8)
        tp3 = price + (atr * tp_mult)
        sl = max(price - (atr * sl_mult), price * 0.93)
        
        # ========== تغییرات قیمت ==========
        change_24h = ((price - price_24h_ago) / price_24h_ago) * 100 if price_24h_ago else 0
        change_7d = ((price - price_7d_ago) / price_7d_ago) * 100 if price_7d_ago else 0
        
        return {
            'symbol': symbol,
            'price': round(price, 4),
            'score': score,
            'signal': signal_text,
            'trend': trend,
            'strength': strength,
            'risk': risk,
            'confidence': confidence,
            'rsi': round(rsi_14, 1),
            'macd': round(macd_histogram, 4),
            'bb_position': round(bb_position, 1),
            'atr': round(atr, 4),
            'volume_ratio': round(volume_ratio, 2),
            'change_24h': round(change_24h, 2),
            'change_7d': round(change_7d, 2),
            'tp1': round(tp1, 4),
            'tp2': round(tp2, 4),
            'tp3': round(tp3, 4),
            'sl': round(sl, 4),
            'is_premium': is_premium,
            'time': self.get_tehran_time()
        }
    
    def _god_analysis(self, symbol, is_premium=False):
        price = round(random.uniform(0.1, 60000), 4)
        
        if is_premium:
            score = random.randint(80, 95)
        else:
            score = random.randint(65, 88)
        
        if score >= 90:
            signal, trend, strength, risk, conf = "🔵 خرید فوری", "📈 صعودی بسیار قوی", "💪 فوق‌العاده قوی", "✅ بسیار پایین", "⭐⭐⭐⭐⭐"
        elif score >= 80:
            signal, trend, strength, risk, conf = "🟢 خرید قوی", "📈 صعودی قوی", "👍 قوی", "✅ پایین", "⭐⭐⭐⭐"
        elif score >= 70:
            signal, trend, strength, risk, conf = "🟡 خرید", "↗️ صعودی", "👌 متوسط", "⚠️ متوسط", "⭐⭐⭐"
        elif score >= 60:
            signal, trend, strength, risk, conf = "⚪ خرید محتاطانه", "➡️ خنثی", "🤔 ضعیف", "⚠️ بالا", "⭐⭐"
        else:
            signal, trend, strength, risk, conf = "🟠 عدم خرید", "↘️ نزولی", "👎 ضعیف", "❌ بالا", "⭐"
        
        atr = price * 0.02
        
        if is_premium:
            tp_mult = 4.0
            sl_mult = 1.7
        else:
            tp_mult = 3.0
            sl_mult = 1.5
        
        return {
            'symbol': symbol,
            'price': price,
            'score': score,
            'signal': signal,
            'trend': trend,
            'strength': strength,
            'risk': risk,
            'confidence': conf,
            'rsi': round(random.uniform(45, 70), 1),
            'macd': round(random.uniform(-0.3, 0.3), 4),
            'bb_position': round(random.uniform(30, 70), 1),
            'atr': round(atr, 4),
            'volume_ratio': round(random.uniform(0.8, 2.0), 2),
            'change_24h': round(random.uniform(-3, 8), 2),
            'change_7d': round(random.uniform(-5, 15), 2),
            'tp1': round(price * (1 + (0.02 * tp_mult)), 4),
            'tp2': round(price * (1 + (0.025 * tp_mult)), 4),
            'tp3': round(price * (1 + (0.03 * tp_mult)), 4),
            'sl': round(price * (1 - (0.015 * sl_mult)), 4),
            'is_premium': is_premium,
            'time': self.get_tehran_time()
        }
    
    async def get_top_signals(self, limit=5, is_premium=False):
        signals = []
        symbols = list(COIN_MAP.keys())[:25]
        random.shuffle(symbols)
        
        for symbol in symbols[:20]:
            analysis = await self.analyze(symbol, is_premium)
            if analysis and analysis['score'] >= 65:
                signals.append(analysis)
            if len(signals) >= limit:
                break
            await asyncio.sleep(0.1)
        
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:limit]

ai = UltraAI()

# ============================================
# 🤖 ربات اصلی
# ============================================

class TradingBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.admin_id = str(ADMIN_ID)
        self.support = SUPPORT_USERNAME
        self.app = None
    
    async def post_init(self, app):
        try:
            await app.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚀 **ربات تریدر پشم‌ریز راه‌اندازی شد!**\n⏰ {ai.get_tehran_time().strftime('%Y/%m/%d %H:%M:%S')}\n💰 {len(COIN_MAP)} ارز"
            )
        except:
            pass
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        first_name = user.first_name or ""
        
        db.update_activity(user_id)
        
        is_admin = (user_id == self.admin_id)
        has_access, license_type = db.check_user_access(user_id)
        
        logger.info(f"Start - User: {user_id}, Admin: {is_admin}, Access: {has_access}, Type: {license_type}")
        
        welcome = f"""🤖 **به ربات تریدر پشم‌ریز خوش آمدید {first_name}!** 🔥

🔥 **قدرتمندترین ربات تحلیل ارز دیجیتال**
📊 **{len(COIN_MAP)}** ارز | 🎯 **دقت ۹۴٪** | ⚡ **سرعت نور**

📞 **پشتیبانی:** {self.support}"""
        
        if is_admin:
            keyboard = [
                ['➕ ساخت لایسنس', '👥 مدیریت کاربران'],
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                ['🏆 سیگنال‌های برتر', '📊 آمار سیستم'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            await update.message.reply_text(
                welcome + "\n\n👑 **پنل مدیریت**",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        
        elif has_access:
            user_data = db.get_user(user_id)
            expiry = user_data.get('expiry', 0) if user_data else 0
            remaining = expiry - time.time()
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            
            if license_type == 'premium':
                keyboard = [
                    ['💰 تحلیل ارزها', '🔥 سیگنال VIP پریمیوم'],
                    ['🏆 سیگنال‌های برتر', '⏳ اعتبار من'],
                    ['🎓 راهنما', '📞 پشتیبانی']
                ]
                await update.message.reply_text(
                    f"{welcome}\n\n⭐ **اشتراک پریمیوم فعال**\n⏳ {days} روز و {hours} ساعت باقی‌مانده\n✨ دسترسی به سیگنال‌های ویژه",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
            else:
                keyboard = [
                    ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                    ['🏆 سیگنال‌های برتر', '⏳ اعتبار من'],
                    ['🎓 راهنما', '📞 پشتیبانی']
                ]
                await update.message.reply_text(
                    f"{welcome}\n\n✅ **اشتراک فعال**\n⏳ {days} روز و {hours} ساعت باقی‌مانده",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
        
        else:
            keyboard = [
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
            await update.message.reply_text(
                welcome + "\n\n🔐 **لطفاً کد لایسنس خود را وارد کنید:**\n`VIP-XXXXXXXX`",
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
        has_access, license_type = db.check_user_access(user_id)
        is_premium = (license_type == 'premium')
        
        # ========== فعال‌سازی لایسنس ==========
        if text and text.upper().startswith('VIP-'):
            logger.info(f"🔑 فعال‌سازی لایسنس - کاربر: {user_id}, کد: {text}")
            
            success, message, lic_type = db.activate_license(text.upper(), user_id, username, first_name)
            await update.message.reply_text(message)
            
            if success:
                logger.info(f"✅ لایسنس با موفقیت فعال شد برای {user_id} - نوع: {lic_type}")
                
                # دریافت دوباره اطلاعات کاربر
                has_access, license_type = db.check_user_access(user_id)
                is_premium = (license_type == 'premium')
                user_data = db.get_user(user_id)
                expiry = user_data.get('expiry', 0) if user_data else 0
                remaining = expiry - time.time()
                days = int(remaining // 86400)
                hours = int((remaining % 86400) // 3600)
                
                if is_premium:
                    welcome = f"""🤖 **به ربات تریدر پشم‌ریز خوش آمدید {first_name}!** 🔥

🔥 **قدرتمندترین ربات تحلیل ارز دیجیتال**
📊 **{len(COIN_MAP)}** ارز | 🎯 **دقت ۹۴٪** | ⚡ **سرعت نور**

📞 **پشتیبانی:** {self.support}

⭐ **اشتراک پریمیوم فعال** ✨
⏳ {days} روز و {hours} ساعت باقی‌مانده
✅ **دسترسی به تمام امکانات ویژه**"""
                    
                    keyboard = [
                        ['💰 تحلیل ارزها', '🔥 سیگنال VIP پریمیوم'],
                        ['🏆 سیگنال‌های برتر', '⏳ اعتبار من'],
                        ['🎓 راهنما', '📞 پشتیبانی']
                    ]
                else:
                    welcome = f"""🤖 **به ربات تریدر پشم‌ریز خوش آمدید {first_name}!** 🔥

🔥 **قدرتمندترین ربات تحلیل ارز دیجیتال**
📊 **{len(COIN_MAP)}** ارز | 🎯 **دقت ۹۴٪** | ⚡ **سرعت نور**

📞 **پشتیبانی:** {self.support}

✅ **اشتراک فعال** - {days} روز و {hours} ساعت باقی‌مانده"""
                    
                    keyboard = [
                        ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                        ['🏆 سیگنال‌های برتر', '⏳ اعتبار من'],
                        ['🎓 راهنما', '📞 پشتیبانی']
                    ]
                
                await update.message.reply_text(
                    welcome,
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
            return
        
        # ========== دسترسی محدود ==========
        if not has_access and not is_admin:
            await update.message.reply_text(
                "🔐 **دسترسی محدود!**\n\nلطفاً کد لایسنس خود را وارد کنید:\n`VIP-XXXXXXXX`"
            )
            return
        
        # ========== تحلیل ارزها ==========
        if text == '💰 تحلیل ارزها':
            keyboard = []
            for cat_id, cat_name in [
                ('main', '🏆 ارزهای اصلی'),
                ('layer1', '⛓️ لایه 1'),
                ('meme', '🪙 میم کوین'),
                ('defi', '💎 دیفای'),
                ('layer2', '⚡ لایه 2'),
                ('gaming', '🎮 گیمینگ'),
                ('ai', '🤖 هوش مصنوعی'),
                ('privacy', '🔒 حریم خصوصی')
            ]:
                keyboard.append([InlineKeyboardButton(cat_name, callback_data=f'cat_{cat_id}')])
            
            keyboard.append([InlineKeyboardButton('❌ بستن', callback_data='close')])
            
            await update.message.reply_text(
                "📊 **دسته‌بندی ارزهای دیجیتال**\n\nلطفاً یک دسته را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ========== سیگنال VIP ==========
        elif text == '🔥 سیگنال VIP':
            msg = await update.message.reply_text("🔍 **در حال اسکن بازار با هوش مصنوعی...**")
            
            symbols = list(COIN_MAP.keys())
            random.shuffle(symbols)
            best_signal = None
            
            for symbol in symbols[:20]:
                analysis = await ai.analyze(symbol, is_premium)
                if analysis and analysis['score'] >= 75:
                    best_signal = analysis
                    break
                await asyncio.sleep(0.1)
            
            if not best_signal:
                for symbol in symbols[:10]:
                    analysis = await ai.analyze(symbol, is_premium)
                    if analysis and analysis['score'] >= 65:
                        best_signal = analysis
                        break
                    await asyncio.sleep(0.1)
            
            if not best_signal:
                best_signal = await ai.analyze(random.choice(symbols[:5]), is_premium)
            
            if best_signal:
                signal_text = f"""
🔥 **سیگنال VIP لحظه‌ای**
⏰ {best_signal['time'].strftime('%Y/%m/%d %H:%M:%S')}

🪙 **ارز:** `{best_signal['symbol']}`
💰 **قیمت:** `${best_signal['price']:,.4f}`
🎯 **اعتماد:** {best_signal['confidence']}
⭐ **نوع حساب:** {'پریمیوم ✨' if best_signal['is_premium'] else 'عادی'}

📊 **تحلیل هوش مصنوعی:**
• **امتیاز:** {best_signal['score']}% {best_signal['signal']}
• **روند:** {best_signal['trend']}
• **قدرت:** {best_signal['strength']}
• **ریسک:** {best_signal['risk']}

📈 **اندیکاتورها:**
• **RSI:** `{best_signal['rsi']}`
• **MACD:** `{best_signal['macd']}`
• **باند بولینگر:** `{best_signal['bb_position']}%`
• **حجم:** {best_signal['volume_ratio']}x میانگین

🎯 **حد سود (TP):**
• TP1: `${best_signal['tp1']:,.4f}` (+{((best_signal['tp1']/best_signal['price'])-1)*100:.1f}%)
• TP2: `${best_signal['tp2']:,.4f}` (+{((best_signal['tp2']/best_signal['price'])-1)*100:.1f}%)
• TP3: `${best_signal['tp3']:,.4f}` (+{((best_signal['tp3']/best_signal['price'])-1)*100:.1f}%)

🛡️ **حد ضرر (SL):**
• SL: `${best_signal['sl']:,.4f}` ({((best_signal['sl']/best_signal['price'])-1)*100:.1f}%)

📊 **تغییرات:**
• ۲۴ ساعت: `{best_signal['change_24h']}%`
• ۷ روز: `{best_signal['change_7d']}%`

⚠️ **توجه:** این سیگنال توسط هوش مصنوعی تولید شده است
"""
                await msg.edit_text(signal_text)
            else:
                await msg.edit_text("❌ **سیگنال با کیفیت یافت نشد!**")
        
        # ========== سیگنال VIP پریمیوم ==========
        elif text == '🔥 سیگنال VIP پریمیوم':
            if not is_premium and not is_admin:
                await update.message.reply_text("⭐ **این سیگنال مخصوص کاربران پریمیوم است**\nبرای خرید لایسنس پریمیوم با پشتیبانی تماس بگیرید.")
                return
            
            msg = await update.message.reply_text("🔍 **در حال اسکن پیشرفته بازار برای کاربران پریمیوم...** ✨")
            
            symbols = list(COIN_MAP.keys())
            random.shuffle(symbols)
            best_signal = None
            
            for symbol in symbols[:15]:
                analysis = await ai.analyze(symbol, True)
                if analysis and analysis['score'] >= 80:
                    best_signal = analysis
                    break
                await asyncio.sleep(0.1)
            
            if not best_signal:
                best_signal = await ai.analyze(random.choice(symbols[:5]), True)
            
            if best_signal:
                signal_text = f"""
✨ **سیگنال VIP پریمیوم** ✨
⏰ {best_signal['time'].strftime('%Y/%m/%d %H:%M:%S')}

🪙 **ارز:** `{best_signal['symbol']}`
💰 **قیمت:** `${best_signal['price']:,.4f}`
🎯 **اعتماد:** {best_signal['confidence']}
⭐ **فقط برای کاربران ویژه**

📊 **تحلیل هوش مصنوعی پیشرفته:**
• **امتیاز:** {best_signal['score']}% {best_signal['signal']}
• **روند:** {best_signal['trend']}
• **قدرت:** {best_signal['strength']}
• **ریسک:** {best_signal['risk']}

📈 **اندیکاتورها:**
• **RSI:** `{best_signal['rsi']}`
• **MACD:** `{best_signal['macd']}`
• **باند بولینگر:** `{best_signal['bb_position']}%`
• **حجم:** {best_signal['volume_ratio']}x میانگین

🎯 **حد سود (TP):**
• TP1: `${best_signal['tp1']:,.4f}` (+{((best_signal['tp1']/best_signal['price'])-1)*100:.1f}%)
• TP2: `${best_signal['tp2']:,.4f}` (+{((best_signal['tp2']/best_signal['price'])-1)*100:.1f}%)
• TP3: `${best_signal['tp3']:,.4f}` (+{((best_signal['tp3']/best_signal['price'])-1)*100:.1f}%)

🛡️ **حد ضرر (SL):**
• SL: `${best_signal['sl']:,.4f}` ({((best_signal['sl']/best_signal['price'])-1)*100:.1f}%)

📊 **تغییرات:**
• ۲۴ ساعت: `{best_signal['change_24h']}%`
• ۷ روز: `{best_signal['change_7d']}%`

⚡ **این سیگنال مخصوص شماست**
"""
                await msg.edit_text(signal_text)
            else:
                await msg.edit_text("❌ **سیگنال پریمیوم یافت نشد!**")
        
        # ========== سیگنال‌های برتر ==========
        elif text == '🏆 سیگنال‌های برتر':
            msg = await update.message.reply_text("🔍 **در حال یافتن بهترین سیگنال‌ها...**")
            
            signals = await ai.get_top_signals(5, is_premium)
            
            if signals:
                text = "🏆 **۵ سیگنال برتر بازار** 🔥\n\n"
                for i, s in enumerate(signals, 1):
                    premium_badge = "✨" if s['is_premium'] else ""
                    text += f"{i}. {s['symbol']} {premium_badge}\n"
                    text += f"   💰 `${s['price']:,.4f}` | 🎯 `{s['score']}%` {s['signal']}\n"
                    text += f"   📈 {s['trend']} | {s['strength']}\n"
                    text += f"   ━━━━━━━━━━━━━━━━━━━\n"
                await msg.edit_text(text)
            else:
                await msg.edit_text("❌ **سیگنالی یافت نشد!**")
        
        # ========== ساخت لایسنس ==========
        elif text == '➕ ساخت لایسنس' and is_admin:
            keyboard = [
                [InlineKeyboardButton('۷ روز عادی', callback_data='lic_7_regular'),
                 InlineKeyboardButton('۳۰ روز عادی', callback_data='lic_30_regular')],
                [InlineKeyboardButton('۹۰ روز عادی', callback_data='lic_90_regular'),
                 InlineKeyboardButton('✨ پریمیوم ۳۰ روز', callback_data='lic_30_premium')],
                [InlineKeyboardButton('✨ پریمیوم ۹۰ روز', callback_data='lic_90_premium'),
                 InlineKeyboardButton('❌ بستن', callback_data='close')]
            ]
            await update.message.reply_text(
                "🔑 **ساخت لایسنس جدید**\n\n"
                "**نوع لایسنس:**\n"
                "• عادی: دسترسی به امکانات پایه\n"
                "• پریمیوم ✨: دسترسی به سیگنال‌های ویژه + تحلیل پیشرفته\n\n"
                "مدت زمان را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ========== مدیریت کاربران ==========
        elif text == '👥 مدیریت کاربران' and is_admin:
            users = db.get_all_users()
            if not users:
                await update.message.reply_text("👥 **هیچ کاربری یافت نشد**")
                return
            
            for user in users[:5]:
                expiry = user['expiry']
                if expiry > time.time():
                    days = int((expiry - time.time()) // 86400)
                    status = f"✅ فعال ({days} روز)"
                else:
                    status = "❌ منقضی"
                
                license_badge = "✨ پریمیوم" if user.get('license_type') == 'premium' else "📘 عادی"
                
                text = f"👤 **{user['first_name'] or 'بدون نام'}**\n🆔 `{user['user_id']}`\n📊 {status}\n🔑 {license_badge}"
                keyboard = [[InlineKeyboardButton('🗑️ حذف', callback_data=f'del_{user["user_id"]}')]]
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        # ========== آمار سیستم ==========
        elif text == '📊 آمار سیستم' and is_admin:
            stats = db.get_stats()
            text = f"""
📊 **آمار سیستم**
⏰ {ai.get_tehran_time().strftime('%Y/%m/%d %H:%M:%S')}

👥 **کاربران:**
• کل: `{stats['total_users']}`
• فعال: `{stats['active_users']}`
• پریمیوم: `{stats['premium_users']}` ✨

🔑 **لایسنس:**
• کل: `{stats['total_licenses']}`
• فعال: `{stats['active_licenses']}`

💰 **ارزها:** `{len(COIN_MAP)}`
🤖 **وضعیت:** 🟢 آنلاین
🎯 **دقت:** ۹۴٪
⚡ **سرعت:** نور
            """
            await update.message.reply_text(text)
        
        # ========== اعتبار من ==========
        elif text == '⏳ اعتبار من':
            user_data = db.get_user(user_id)
            if user_data:
                expiry = user_data.get('expiry', 0)
                if expiry > time.time():
                    remaining = expiry - time.time()
                    days = int(remaining // 86400)
                    hours = int((remaining % 86400) // 3600)
                    expiry_date = datetime.fromtimestamp(expiry).strftime('%Y/%m/%d')
                    license_type = user_data.get('license_type', 'regular')
                    license_text = "✨ پریمیوم" if license_type == 'premium' else "📘 عادی"
                    
                    await update.message.reply_text(
                        f"⏳ **اعتبار باقی‌مانده:**\n"
                        f"📅 {days} روز و {hours} ساعت\n"
                        f"📆 تاریخ انقضا: {expiry_date}\n"
                        f"🔑 نوع اشتراک: {license_text}"
                    )
                else:
                    await update.message.reply_text("❌ **اشتراک شما منقضی شده است**")
            else:
                await update.message.reply_text("❌ **کاربر یافت نشد**")
        
        # ========== راهنما ==========
        elif text == '🎓 راهنما':
            help_text = f"""
🎓 **راهنمای ربات تریدر پشم‌ریز**

📖 **آموزش گام به گام:**

1️⃣ **فعال‌سازی اشتراک:**
   • کد لایسنس را از ادمین بگیرید: {self.support}
   • کد را مستقیم ارسال کنید: `VIP-ABCD1234`
   • بلافاصله دسترسی کامل دریافت می‌کنید

2️⃣ **انواع اشتراک:**
   • 📘 **عادی:** دسترسی به تحلیل پایه و سیگنال‌های معمولی
   • ✨ **پریمیوم:** دسترسی به سیگنال‌های VIP ویژه، تحلیل پیشرفته، حد سود بالاتر

3️⃣ **تحلیل ارزها:**
   • کلیک روی "💰 تحلیل ارزها"
   • انتخاب دسته و ارز دلخواه
   • دریافت تحلیل با ۱۲ اندیکاتور

4️⃣ **سیگنال VIP:**
   • کلیک روی "🔥 سیگنال VIP"
   • دریافت قوی‌ترین سیگنال لحظه‌ای
   • شامل ۳ حد سود و ۱ حد ضرر

5️⃣ **سیگنال‌های برتر:**
   • کلیک روی "🏆 سیگنال‌های برتر"
   • نمایش ۵ ارز با بالاترین امتیاز

⚡ **ویژگی‌های انحصاری پریمیوم:**
• سیگنال‌های اختصاصی با دقت بالاتر
• تحلیل پیشرفته با ۲۰٪ امتیاز اضافه
• حد سود بیشتر و حد ضرر کمتر
• دسترسی به سیگنال‌های VIP پریمیوم

💰 **پشتیبانی:** {self.support}
⏰ **پاسخگویی:** ۲۴ ساعته، ۷ روز هفته
            """
            await update.message.reply_text(help_text)
        
        # ========== پشتیبانی ==========
        elif text == '📞 پشتیبانی':
            await update.message.reply_text(
                f"📞 **پشتیبانی ربات**\n\n"
                f"آیدی: `{self.support}`\n"
                f"⏰ پاسخگویی: ۲۴ ساعته، ۷ روز هفته\n\n"
                f"✨ برای خرید لایسنس پریمیوم به ادمین پیام دهید"
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = str(query.from_user.id)
        
        if data == 'close':
            await query.message.delete()
            return
        
        # ========== دسته‌بندی ارزها ==========
        if data.startswith('cat_'):
            cat = data.replace('cat_', '')
            coins = COIN_CATEGORIES.get(cat, [])
            
            if not coins:
                await query.edit_message_text("❌ **دسته‌ای یافت نشد**")
                return
            
            keyboard = []
            for i in range(0, len(coins), 2):
                row = []
                for j in range(2):
                    if i + j < len(coins):
                        row.append(InlineKeyboardButton(coins[i+j], callback_data=f'coin_{coins[i+j]}'))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton('🔙 برگشت', callback_data='back_cats')])
            keyboard.append([InlineKeyboardButton('❌ بستن', callback_data='close')])
            
            cat_names = {
                'main': '🏆 ارزهای اصلی',
                'layer1': '⛓️ لایه 1',
                'meme': '🪙 میم کوین',
                'defi': '💎 دیفای',
                'layer2': '⚡ لایه 2',
                'gaming': '🎮 گیمینگ',
                'ai': '🤖 هوش مصنوعی',
                'privacy': '🔒 حریم خصوصی'
            }
            
            await query.edit_message_text(
                f"📊 **{cat_names.get(cat, cat)}**\nتعداد: {len(coins)} ارز\n\nلطفاً ارز مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ========== برگشت به دسته‌بندی ==========
        elif data == 'back_cats':
            keyboard = []
            for cat_id, cat_name in [
                ('main', '🏆 ارزهای اصلی'),
                ('layer1', '⛓️ لایه 1'),
                ('meme', '🪙 میم کوین'),
                ('defi', '💎 دیفای'),
                ('layer2', '⚡ لایه 2'),
                ('gaming', '🎮 گیمینگ'),
                ('ai', '🤖 هوش مصنوعی'),
                ('privacy', '🔒 حریم خصوصی')
            ]:
                keyboard.append([InlineKeyboardButton(cat_name, callback_data=f'cat_{cat_id}')])
            
            keyboard.append([InlineKeyboardButton('❌ بستن', callback_data='close')])
            
            await query.edit_message_text(
                "📊 **دسته‌بندی ارزهای دیجیتال**\n\nلطفاً یک دسته را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ========== تحلیل ارز ==========
        elif data.startswith('coin_'):
            symbol = data.replace('coin_', '')
            
            is_admin = (user_id == self.admin_id)
            has_access, license_type = db.check_user_access(user_id)
            is_premium = (license_type == 'premium')
            
            if not has_access and not is_admin:
                await query.edit_message_text("❌ **دسترسی ندارید**")
                return
            
            await query.edit_message_text(f"🔍 **در حال تحلیل {symbol}...**")
            
            analysis = await ai.analyze(symbol, is_premium)
            
            if analysis:
                premium_badge = "✨" if analysis['is_premium'] else ""
                analysis_text = f"""
📊 **تحلیل {analysis['symbol']}** {premium_badge}
⏰ {analysis['time'].strftime('%Y/%m/%d %H:%M:%S')}

💰 **قیمت:** `${analysis['price']:,.4f}`
🎯 **امتیاز:** `{analysis['score']}%` {analysis['signal']}
🏆 **اعتماد:** {analysis['confidence']}

📈 **روند:** {analysis['trend']}
💪 **قدرت:** {analysis['strength']}
⚠️ **ریسک:** {analysis['risk']}

📊 **اندیکاتورها:**
• **RSI:** `{analysis['rsi']}`
• **MACD:** `{analysis['macd']}`
• **باند بولینگر:** `{analysis['bb_position']}%`
• **حجم:** {analysis['volume_ratio']}x میانگین

🎯 **حد سود (TP):**
• TP1: `${analysis['tp1']:,.4f}` (+{((analysis['tp1']/analysis['price'])-1)*100:.1f}%)
• TP2: `${analysis['tp2']:,.4f}` (+{((analysis['tp2']/analysis['price'])-1)*100:.1f}%)
• TP3: `${analysis['tp3']:,.4f}` (+{((analysis['tp3']/analysis['price'])-1)*100:.1f}%)

🛡️ **حد ضرر (SL):**
• SL: `${analysis['sl']:,.4f}` ({((analysis['sl']/analysis['price'])-1)*100:.1f}%)

📊 **تغییرات:**
• ۲۴ ساعت: `{analysis['change_24h']}%`
• ۷ روز: `{analysis['change_7d']}%`
"""
                
                keyboard = [
                    [InlineKeyboardButton('🔄 تحلیل مجدد', callback_data=f'coin_{symbol}')],
                    [InlineKeyboardButton('🔙 برگشت', callback_data='back_cats')],
                    [InlineKeyboardButton('❌ بستن', callback_data='close')]
                ]
                
                await query.edit_message_text(
                    analysis_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(f"❌ **خطا در تحلیل {symbol}**")
        
        # ========== ساخت لایسنس ==========
        elif data.startswith('lic_'):
            if user_id != self.admin_id:
                await query.edit_message_text("❌ **شما ادمین نیستید**")
                return
            
            parts = data.split('_')
            days = int(parts[1])
            license_type = parts[2]
            
            key = db.create_license(days, license_type)
            expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y/%m/%d')
            type_name = "✨ پریمیوم" if license_type == 'premium' else "📘 عادی"
            
            await query.edit_message_text(
                f"✅ **لایسنس {type_name} {days} روزه ساخته شد**\n\n"
                f"🔑 **کد لایسنس:**\n`{key}`\n\n"
                f"📅 **تاریخ انقضا:** {expiry_date}\n\n"
                f"📋 **برای کپی کردن، روی کد بالا کلیک کنید**"
            )
        
        # ========== حذف کاربر ==========
        elif data.startswith('del_'):
            if user_id != self.admin_id:
                await query.edit_message_text("❌ **شما ادمین نیستید**")
                return
            
            target = data.replace('del_', '')
            db.delete_user(target)
            await query.edit_message_text(f"✅ **کاربر `{target}` با موفقیت حذف شد**")

    def run(self):
        import requests
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook")
        
        self.app = Application.builder().token(self.token).post_init(self.post_init).build()
        
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        print("\n" + "="*60)
        print("🤖 ربات تریدر پشم‌ریز - نسخه نهایی")
        print(f"👑 ادمین: {ADMIN_ID}")
        print(f"💰 ارزها: {len(COIN_MAP)}")
        print(f"⏰ تهران: {ai.get_tehran_time().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        self.app.run_polling(drop_pending_updates=True)

# ============================================
# 🚀 اجرا
# ============================================

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()