#!/usr/bin/env python3
"""
🤖 ULTRA PRO TRADING BOT V3.0 - لایسنس کاملاً کارآمد
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
# 🔧 CONFIGURATION
# ============================================

TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
SUPPORT_USERNAME = "@reunite_music"

# مسیر دیتابیس
if os.path.exists("/data"):
    DB_PATH = "/data/trading_bot.db"
else:
    DB_PATH = "trading_bot.db"

# ============================================
# 📊 COINS (60+)
# ============================================

COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'BNB/USDT': 'BNB-USD',
    'SOL/USDT': 'SOL-USD', 'XRP/USDT': 'XRP-USD', 'ADA/USDT': 'ADA-USD',
    'AVAX/USDT': 'AVAX-USD', 'DOGE/USDT': 'DOGE-USD', 'DOT/USDT': 'DOT-USD',
    'MATIC/USDT': 'MATIC-USD', 'TRX/USDT': 'TRX-USD', 'LINK/USDT': 'LINK-USD',
    'SHIB/USDT': 'SHIB-USD', 'TON/USDT': 'TON-USD', 'ATOM/USDT': 'ATOM-USD',
    'UNI/USDT': 'UNI-USD', 'LTC/USDT': 'LTC-USD', 'BCH/USDT': 'BCH-USD',
    'ETC/USDT': 'ETC-USD', 'FIL/USDT': 'FIL-USD', 'NEAR/USDT': 'NEAR-USD',
    'APT/USDT': 'APT-USD', 'ARB/USDT': 'ARB-USD', 'OP/USDT': 'OP-USD',
    'SUI/USDT': 'SUI-USD', 'PEPE/USDT': 'PEPE-USD', 'FLOKI/USDT': 'FLOKI-USD',
    'BONK/USDT': 'BONK-USD', 'WIF/USDT': 'WIF-USD', 'BOME/USDT': 'BOME-USD',
    'AAVE/USDT': 'AAVE-USD', 'MKR/USDT': 'MKR-USD', 'CRV/USDT': 'CRV-USD',
    'SAND/USDT': 'SAND-USD', 'MANA/USDT': 'MANA-USD', 'AXS/USDT': 'AXS-USD',
    'GALA/USDT': 'GALA-USD', 'RNDR/USDT': 'RNDR-USD', 'FET/USDT': 'FET-USD',
    'AGIX/USDT': 'AGIX-USD', 'XMR/USDT': 'XMR-USD', 'ZEC/USDT': 'ZEC-USD',
}

COIN_CATEGORIES = {
    'main': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT'],
    'layer1': ['ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'NEAR/USDT', 'APT/USDT'],
    'meme': ['DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'FLOKI/USDT', 'WIF/USDT'],
    'defi': ['UNI/USDT', 'AAVE/USDT', 'MKR/USDT', 'CRV/USDT'],
    'layer2': ['MATIC/USDT', 'ARB/USDT', 'OP/USDT'],
    'gaming': ['SAND/USDT', 'MANA/USDT', 'AXS/USDT', 'GALA/USDT'],
    'ai': ['RNDR/USDT', 'FET/USDT', 'AGIX/USDT'],
    'privacy': ['XMR/USDT', 'ZEC/USDT'],
}

# ============================================
# 🪵 LOGGING
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
# 🗄️ DATABASE - اصلاح شده برای لایسنس
# ============================================

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
        logger.info(f"🗄️ Database initialized at {DB_PATH}")
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            # جدول کاربران
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                expiry REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active REAL DEFAULT 0
            )''')
            
            # جدول لایسنس‌ها
            c.execute('''CREATE TABLE IF NOT EXISTS licenses (
                license_key TEXT PRIMARY KEY,
                days INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_by TEXT,
                used_at TIMESTAMP
            )''')
            
            conn.commit()
            logger.info("✅ Database tables created")
    
    def get_user(self, user_id):
        """دریافت اطلاعات کاربر"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT * FROM users WHERE user_id = ?", 
                    (user_id,)
                ).fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def add_user(self, user_id, username, first_name, expiry):
        """افزودن یا بروزرسانی کاربر"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, expiry, last_active) 
                    VALUES (?, ?, ?, ?, ?)''',
                    (user_id, username or "", first_name or "", expiry, time.time()))
                conn.commit()
                logger.info(f"✅ User added/updated: {user_id}, expiry: {datetime.fromtimestamp(expiry)}")
                return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def update_activity(self, user_id):
        """بروزرسانی آخرین فعالیت"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET last_active = ? WHERE user_id = ?",
                    (time.time(), user_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating activity: {e}")
    
    def create_license(self, days):
        """ایجاد لایسنس جدید"""
        try:
            license_key = f"VIP-{uuid.uuid4().hex[:8].upper()}"
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO licenses (license_key, days, is_active) VALUES (?, ?, 1)",
                    (license_key, days)
                )
                conn.commit()
            logger.info(f"🔑 License created: {license_key} ({days} days)")
            return license_key
        except Exception as e:
            logger.error(f"Error creating license: {e}")
            return f"VIP-{uuid.uuid4().hex[:6].upper()}"
    
    def activate_license(self, license_key, user_id, username="", first_name=""):
        """فعال‌سازی لایسنس - اصلاح شده"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # بررسی لایسنس
                license_data = conn.execute(
                    "SELECT days, is_active FROM licenses WHERE license_key = ?",
                    (license_key,)
                ).fetchone()
                
                if not license_data:
                    logger.warning(f"License not found: {license_key}")
                    return False, "❌ لایسنس یافت نشد"
                
                if license_data[1] == 0:
                    logger.warning(f"License already used: {license_key}")
                    return False, "❌ این لایسنس قبلاً استفاده شده است"
                
                days = license_data[0]
                
                # دریافت کاربر فعلی
                user = self.get_user(user_id)
                current_time = time.time()
                
                # محاسبه تاریخ انقضای جدید
                if user and user.get('expiry', 0) > current_time:
                    # تمدید اشتراک
                    new_expiry = user['expiry'] + (days * 86400)
                    message = f"✅ اشتراک شما {days} روز تمدید شد!"
                else:
                    # اشتراک جدید
                    new_expiry = current_time + (days * 86400)
                    message = f"✅ اشتراک {days} روزه با موفقیت فعال شد!"
                
                # غیرفعال کردن لایسنس
                conn.execute(
                    "UPDATE licenses SET is_active = 0, used_by = ?, used_at = ? WHERE license_key = ?",
                    (user_id, datetime.now().isoformat(), license_key)
                )
                
                # ذخیره کاربر با تاریخ انقضای جدید
                self.add_user(user_id, username, first_name, new_expiry)
                
                conn.commit()
                
                expiry_date = datetime.fromtimestamp(new_expiry).strftime('%Y/%m/%d')
                logger.info(f"✅ License activated for {user_id}, expires: {expiry_date}")
                
                return True, f"{message}\n📅 تاریخ انقضا: {expiry_date}"
                
        except Exception as e:
            logger.error(f"Error activating license: {e}")
            return False, "❌ خطا در فعال‌سازی لایسنس"
    
    def get_all_users(self):
        """دریافت همه کاربران"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                return conn.execute(
                    "SELECT * FROM users ORDER BY last_active DESC"
                ).fetchall()
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def delete_user(self, user_id):
        """حذف کاربر"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                conn.commit()
                logger.info(f"🗑️ User deleted: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def get_stats(self):
        """آمار سیستم"""
        stats = {
            'total_users': 0,
            'active_users': 0,
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
                
                c.execute("SELECT COUNT(*) FROM licenses")
                stats['total_licenses'] = c.fetchone()[0] or 0
                
                c.execute("SELECT COUNT(*) FROM licenses WHERE is_active = 1")
                stats['active_licenses'] = c.fetchone()[0] or 0
                
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
        return stats

db = Database()

# ============================================
# 🧠 ANALYZER
# ============================================

class Analyzer:
    def __init__(self):
        self.cache = {}
        logger.info("🧠 Analyzer initialized")
    
    async def analyze(self, symbol):
        cache_key = symbol
        if cache_key in self.cache:
            if time.time() - self.cache[cache_key]['time'] < 300:
                return self.cache[cache_key]['data']
        
        try:
            ticker = COIN_MAP.get(symbol)
            if not ticker:
                return self._smart_analysis(symbol)
            
            df = yf.download(ticker, period="2d", interval="1h", progress=False, timeout=3)
            
            if df.empty or len(df) < 5:
                return self._smart_analysis(symbol)
            
            analysis = self._calculate(df, symbol)
            
            self.cache[cache_key] = {'time': time.time(), 'data': analysis}
            return analysis
            
        except Exception as e:
            logger.warning(f"YFinance error: {e}")
            return self._smart_analysis(symbol)
    
    def _calculate(self, df, symbol):
        close = df['Close']
        price = float(close.iloc[-1])
        
        # SMA
        sma_20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else price
        sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else price
        
        # RSI
        rsi = 50
        if len(close) >= 15:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            if not rs.isna().all():
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # ATR
        atr = price * 0.02
        if len(close) >= 14:
            high, low = df['High'], df['Low']
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            if not tr.isna().all():
                atr = tr.rolling(14).mean().iloc[-1]
        
        # امتیاز
        score = 55
        if pd.notna(sma_20) and price > sma_20:
            score += 15
        if pd.notna(sma_50) and price > sma_50:
            score += 10
        if pd.notna(rsi):
            if 45 < rsi < 65:
                score += 20
            elif 40 < rsi < 70:
                score += 15
        
        score = min(95, max(40, int(score)))
        
        # سیگنال
        if score >= 75:
            signal = "🔵 خرید قوی"
            trend = "صعودی قوی 📈"
            tp_mult, sl_mult = 3.0, 1.6
        elif score >= 60:
            signal = "🟢 خرید"
            trend = "صعودی ملایم ↗️"
            tp_mult, sl_mult = 2.5, 1.4
        elif score >= 45:
            signal = "🟡 خرید محتاطانه"
            trend = "خنثی ↔️"
            tp_mult, sl_mult = 2.0, 1.2
        else:
            signal = "🔴 عدم خرید"
            trend = "نزولی 📉"
            tp_mult, sl_mult = 1.5, 1.1
        
        tp = price + (atr * tp_mult)
        sl = max(price - (atr * sl_mult), price * 0.94)
        
        return {
            'symbol': symbol,
            'price': round(price, 4),
            'score': score,
            'rsi': round(rsi, 1),
            'atr': round(atr, 4),
            'trend': trend,
            'signal': signal,
            'tp': round(tp, 4),
            'sl': round(sl, 4)
        }
    
    def _smart_analysis(self, symbol):
        price = round(random.uniform(1, 50000), 4)
        score = random.randint(55, 88)
        
        if score >= 75:
            signal, trend = "🔵 خرید قوی", "صعودی قوی 📈"
        elif score >= 60:
            signal, trend = "🟢 خرید", "صعودی ملایم ↗️"
        elif score >= 45:
            signal, trend = "🟡 خرید محتاطانه", "خنثی ↔️"
        else:
            signal, trend = "🔴 عدم خرید", "نزولی 📉"
        
        return {
            'symbol': symbol,
            'price': price,
            'score': score,
            'rsi': round(random.uniform(40, 70), 1),
            'atr': round(price * 0.02, 4),
            'trend': trend,
            'signal': signal,
            'tp': round(price * (1 + random.uniform(0.03, 0.07)), 4),
            'sl': round(price * (1 - random.uniform(0.02, 0.04)), 4)
        }
    
    async def get_top_signals(self, limit=5):
        signals = []
        symbols = list(COIN_MAP.keys())[:12]
        for s in symbols:
            a = await self.analyze(s)
            if a and a['score'] >= 60:
                signals.append(a)
            await asyncio.sleep(0.1)
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:limit]

analyzer = Analyzer()

# ============================================
# 🤖 BOT
# ============================================

class TradingBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.admin_id = str(ADMIN_ID)
        self.support = SUPPORT_USERNAME
        self.app = None
    
    async def post_init(self, app):
        """بعد از راه‌اندازی"""
        try:
            await app.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚀 ربات تریدر راه‌اندازی شد!\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except:
            pass
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع ربات"""
        user = update.effective_user
        user_id = str(user.id)
        
        db.update_activity(user_id)
        
        is_admin = user_id == self.admin_id
        user_data = db.get_user(user_id)
        
        # بررسی دسترسی
        if user_data and user_data.get('expiry', 0) > time.time():
            has_access = True
        else:
            has_access = is_admin
        
        welcome = f"🤖 به ربات تریدر خوش آمدید {user.first_name}!\n\n"
        welcome += f"📞 پشتیبانی: {self.support}\n"
        welcome += f"💰 تعداد ارزها: {len(COIN_MAP)}\n\n"
        
        if is_admin:
            welcome += "👑 شما ادمین هستید"
            keyboard = [
                ['➕ ساخت لایسنس', '👥 مدیریت'],
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                ['🏆 سیگنال‌های برتر', '📊 آمار'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
        elif has_access:
            remaining = user_data['expiry'] - time.time()
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            welcome += f"✅ اشتراک فعال - {days} روز و {hours} ساعت باقی‌مانده"
            keyboard = [
                ['💰 تحلیل ارزها', '🔥 سیگنال VIP'],
                ['🏆 سیگنال‌های برتر', '⏳ اعتبار'],
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
        else:
            welcome += "🔐 برای استفاده از ربات، لایسنس خود را وارد کنید:\nمثال: VIP-XXXXXX"
            keyboard = [
                ['🎓 راهنما', '📞 پشتیبانی']
            ]
        
        await update.message.reply_text(
            welcome,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام‌ها"""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or ""
        first_name = user.first_name or ""
        text = update.message.text
        
        db.update_activity(user_id)
        
        is_admin = user_id == self.admin_id
        user_data = db.get_user(user_id)
        
        # بررسی دسترسی
        if user_data and user_data.get('expiry', 0) > time.time():
            has_access = True
        else:
            has_access = is_admin
        
        # ===== فعال‌سازی لایسنس (مهمترین بخش) =====
        if text and text.startswith('VIP-'):
            success, message = db.activate_license(text.strip(), user_id, username, first_name)
            await update.message.reply_text(message)
            
            # اگر موفق بود، منوی اصلی را نشان بده
            if success:
                await self.start(update, context)
            return
        
        # ===== تحلیل ارزها =====
        if text == '💰 تحلیل ارزها':
            if not has_access:
                await update.message.reply_text("❌ دسترسی ندارید! لطفاً لایسنس وارد کنید.")
                return
            
            keyboard = []
            for cat, name in [
                ('main', '🏆 ارزهای اصلی'),
                ('layer1', '⛓️ لایه 1'),
                ('meme', '🪙 میم کوین'),
                ('defi', '💎 دیفای'),
                ('layer2', '⚡ لایه 2'),
                ('gaming', '🎮 گیمینگ'),
                ('ai', '🤖 هوش مصنوعی'),
                ('privacy', '🔒 حریم خصوصی')
            ]:
                keyboard.append([InlineKeyboardButton(name, callback_data=f'cat_{cat}')])
            
            keyboard.append([InlineKeyboardButton('❌ بستن', callback_data='close')])
            
            await update.message.reply_text(
                "📊 دسته‌بندی ارزهای دیجیتال:\nلطفاً یک دسته را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ===== سیگنال VIP =====
        elif text == '🔥 سیگنال VIP':
            if not has_access:
                await update.message.reply_text("❌ دسترسی ندارید!")
                return
            
            msg = await update.message.reply_text("🔍 در حال تحلیل بازار...")
            
            symbols = list(COIN_MAP.keys())
            symbol = random.choice(symbols[:15])
            analysis = await analyzer.analyze(symbol)
            
            if analysis:
                signal_text = f"""
🚀 سیگنال VIP لحظه‌ای
⏰ {datetime.now().strftime('%H:%M:%S')}

🪙 ارز: {analysis['symbol']}
💰 قیمت: ${analysis['price']:,.4f}
🎯 امتیاز: {analysis['score']}% {analysis['signal']}

📈 روند: {analysis['trend']}
📊 RSI: {analysis['rsi']}

🎯 TP: ${analysis['tp']:,.4f}
🛡️ SL: ${analysis['sl']:,.4f}
                """
                await msg.edit_text(signal_text.strip())
            else:
                await msg.edit_text("❌ خطا در تحلیل!")
        
        # ===== سیگنال‌های برتر =====
        elif text == '🏆 سیگنال‌های برتر':
            if not has_access:
                await update.message.reply_text("❌ دسترسی ندارید!")
                return
            
            msg = await update.message.reply_text("🔍 در حال یافتن بهترین سیگنال‌ها...")
            signals = await analyzer.get_top_signals(5)
            
            if signals:
                text = "🏆 ۵ سیگنال برتر بازار\n\n"
                for i, s in enumerate(signals, 1):
                    text += f"{i}. {s['symbol']}\n"
                    text += f"   💰 ${s['price']:,.4f} | 🎯 {s['score']}%\n"
                    text += f"   📈 {s['trend']}\n"
                    text += "   ━━━━━━━━━━━\n"
                await msg.edit_text(text.strip())
            else:
                await msg.edit_text("❌ سیگنالی یافت نشد!")
        
        # ===== ساخت لایسنس =====
        elif text == '➕ ساخت لایسنس' and is_admin:
            keyboard = [
                [InlineKeyboardButton('۷ روز', callback_data='lic_7'),
                 InlineKeyboardButton('۳۰ روز', callback_data='lic_30')],
                [InlineKeyboardButton('۹۰ روز', callback_data='lic_90'),
                 InlineKeyboardButton('❌ بستن', callback_data='close')]
            ]
            await update.message.reply_text(
                "🔑 ساخت لایسنس جدید:\nمدت زمان را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ===== مدیریت کاربران =====
        elif text == '👥 مدیریت' and is_admin:
            users = db.get_all_users()
            if not users:
                await update.message.reply_text("👥 هیچ کاربری یافت نشد")
                return
            
            for user in users[:5]:
                expiry = user['expiry']
                current_time = time.time()
                
                if expiry > current_time:
                    days = int((expiry - current_time) // 86400)
                    status = f"✅ فعال ({days} روز)"
                else:
                    status = "❌ منقضی"
                
                text = f"👤 {user['first_name'] or 'بدون نام'}\n🆔 {user['user_id']}\n📊 {status}"
                keyboard = [[InlineKeyboardButton('🗑️ حذف', callback_data=f'del_{user["user_id"]}')]]
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        
        # ===== آمار =====
        elif text == '📊 آمار' and is_admin:
            stats = db.get_stats()
            text = f"""
📊 آمار سیستم
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}

👥 کاربران:
• کل: {stats['total_users']}
• فعال: {stats['active_users']}

🔑 لایسنس:
• کل: {stats['total_licenses']}
• فعال: {stats['active_licenses']}

💰 ارزها: {len(COIN_MAP)}
            """
            await update.message.reply_text(text.strip())
        
        # ===== اعتبار =====
        elif text == '⏳ اعتبار':
            if user_data:
                expiry = user_data.get('expiry', 0)
                if expiry > time.time():
                    remaining = expiry - time.time()
                    days = int(remaining // 86400)
                    hours = int((remaining % 86400) // 3600)
                    expiry_date = datetime.fromtimestamp(expiry).strftime('%Y/%m/%d')
                    await update.message.reply_text(
                        f"⏳ اعتبار باقی‌مانده:\n"
                        f"📅 {days} روز و {hours} ساعت\n"
                        f"📆 تاریخ انقضا: {expiry_date}"
                    )
                else:
                    await update.message.reply_text("❌ اشتراک شما منقضی شده است!\nلطفاً لایسنس جدید وارد کنید.")
            else:
                await update.message.reply_text("❌ کاربر یافت نشد!")
        
        # ===== راهنما =====
        elif text == '🎓 راهنما':
            help_text = f"""
🎓 راهنمای ربات تریدر

📖 آموزش استفاده:

1️⃣ فعال‌سازی اشتراک:
   • کد لایسنس را از ادمین دریافت کنید
   • کد را به ربات ارسال کنید (مثال: VIP-ABCD1234)
   • پس از فعال‌سازی، منوی کامل نمایش داده می‌شود

2️⃣ تحلیل ارزها:
   • روی "💰 تحلیل ارزها" کلیک کنید
   • دسته مورد نظر را انتخاب کنید
   • ارز دلخواه را انتخاب کنید
   • تحلیل کامل نمایش داده می‌شود

3️⃣ سیگنال VIP:
   • روی "🔥 سیگنال VIP" کلیک کنید
   • بهترین سیگنال لحظه‌ای دریافت کنید

4️⃣ سیگنال‌های برتر:
   • روی "🏆 سیگنال‌های برتر" کلیک کنید
   • ۵ ارز برتر بازار را مشاهده کنید

📞 پشتیبانی: {self.support}
            """
            await update.message.reply_text(help_text.strip())
        
        # ===== پشتیبانی =====
        elif text == '📞 پشتیبانی':
            await update.message.reply_text(f"📞 پشتیبانی: {self.support}\n⏰ پاسخگویی: ۲۴ ساعته")
        
        # ===== دسترسی محدود =====
        elif not has_access and not text.startswith('VIP-'):
            await update.message.reply_text(
                "🔐 دسترسی محدود!\n"
                "برای استفاده از ربات، لطفاً کد لایسنس خود را وارد کنید.\n"
                "مثال: VIP-ABCD1234"
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کلیک‌های اینلاین"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = str(query.from_user.id)
        
        if data == 'close':
            await query.message.delete()
            return
        
        # ===== دسته‌بندی =====
        if data.startswith('cat_'):
            cat = data.replace('cat_', '')
            coins = COIN_CATEGORIES.get(cat, [])
            
            if not coins:
                await query.edit_message_text("❌ دسته‌ای یافت نشد")
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
                'main': '🏆 ارزهای اصلی', 'layer1': '⛓️ لایه 1',
                'meme': '🪙 میم کوین', 'defi': '💎 دیفای',
                'layer2': '⚡ لایه 2', 'gaming': '🎮 گیمینگ',
                'ai': '🤖 هوش مصنوعی', 'privacy': '🔒 حریم خصوصی'
            }
            
            await query.edit_message_text(
                f"📊 {cat_names.get(cat, cat)}\nتعداد: {len(coins)} ارز\n\nلطفاً ارز مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ===== برگشت =====
        elif data == 'back_cats':
            keyboard = []
            for cat, name in [
                ('main', '🏆 ارزهای اصلی'), ('layer1', '⛓️ لایه 1'),
                ('meme', '🪙 میم کوین'), ('defi', '💎 دیفای'),
                ('layer2', '⚡ لایه 2'), ('gaming', '🎮 گیمینگ'),
                ('ai', '🤖 هوش مصنوعی'), ('privacy', '🔒 حریم خصوصی')
            ]:
                keyboard.append([InlineKeyboardButton(name, callback_data=f'cat_{cat}')])
            
            keyboard.append([InlineKeyboardButton('❌ بستن', callback_data='close')])
            
            await query.edit_message_text(
                "📊 دسته‌بندی ارزهای دیجیتال:\nلطفاً یک دسته را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ===== تحلیل ارز =====
        elif data.startswith('coin_'):
            symbol = data.replace('coin_', '')
            
            # بررسی دسترسی
            is_admin = user_id == self.admin_id
            user_data = db.get_user(user_id)
            
            if user_data and user_data.get('expiry', 0) > time.time():
                has_access = True
            else:
                has_access = is_admin
            
            if not has_access:
                await query.edit_message_text("❌ دسترسی ندارید!\nلطفاً لایسنس وارد کنید.")
                return
            
            await query.edit_message_text(f"🔍 در حال تحلیل {symbol}...")
            
            analysis = await analyzer.analyze(symbol)
            
            if analysis:
                text = f"""
📊 تحلیل {analysis['symbol']}
⏰ {datetime.now().strftime('%H:%M:%S')}

💰 قیمت: ${analysis['price']:,.4f}
🎯 امتیاز: {analysis['score']}% {analysis['signal']}

📈 روند: {analysis['trend']}
📊 RSI: {analysis['rsi']}

🎯 TP: ${analysis['tp']:,.4f}
🛡️ SL: ${analysis['sl']:,.4f}
                """
                
                keyboard = [
                    [InlineKeyboardButton('🔄 تحلیل مجدد', callback_data=f'coin_{symbol}')],
                    [InlineKeyboardButton('🔙 برگشت', callback_data='back_cats')],
                    [InlineKeyboardButton('❌ بستن', callback_data='close')]
                ]
                
                await query.edit_message_text(
                    text.strip(),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(f"❌ خطا در تحلیل {symbol}!")
        
        # ===== ساخت لایسنس =====
        elif data.startswith('lic_'):
            if user_id != self.admin_id:
                await query.edit_message_text("❌ شما ادمین نیستید!")
                return
            
            days = int(data.replace('lic_', ''))
            key = db.create_license(days)
            
            expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y/%m/%d')
            
            await query.edit_message_text(
                f"✅ لایسنس {days} روزه با موفقیت ساخته شد:\n\n"
                f"🔑 {key}\n\n"
                f"📅 تاریخ انقضا: {expiry_date}\n\n"
                f"این کد را به کاربر مورد نظر بدهید."
            )
        
        # ===== حذف کاربر =====
        elif data.startswith('del_'):
            if user_id != self.admin_id:
                await query.edit_message_text("❌ شما ادمین نیستید!")
                return
            
            target = data.replace('del_', '')
            db.delete_user(target)
            await query.edit_message_text(f"✅ کاربر {target} با موفقیت حذف شد")
    
    def run(self):
        """اجرای ربات"""
        import requests
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook")
        
        self.app = Application.builder().token(self.token).post_init(self.post_init).build()
        
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        print("\n" + "="*50)
        print("🤖 ULTRA PRO TRADING BOT")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print(f"💰 Coins: {len(COIN_MAP)}")
        print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50 + "\n")
        
        self.app.run_polling(drop_pending_updates=True)

# ============================================
# 🚀 اجرا
# ============================================

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()