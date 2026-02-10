import os
import sys
import json
import time
import uuid
import math
import sqlite3
import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from contextlib import closing

# کتابخانه‌های اصلی
import yfinance as yf
import pandas as pd
import numpy as np

# matplotlib برای محیط بدون GUI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io

# کتابخانه تلگرام
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ============================================
# 🔧 CONFIGURATION - تنظیمات اصلی
# ============================================

# توکن تلگرام و آیدی ادمین
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770

# مسیرهای فایل
if os.path.exists("/data"):
    DATA_DIR = "/data"
    DB_PATH = os.path.join(DATA_DIR, "trading_bot.db")
else:
    DATA_DIR = "."
    DB_PATH = "trading_bot.db"

LOG_FILE = "bot.log"

# تنظیمات تحلیل
ANALYSIS_TIMEFRAME = "1h"
ANALYSIS_PERIOD = "7d"  # کاهش دوره برای سرعت بیشتر
MIN_WIN_RATE = 60

# لیست ارزها
COIN_MAP = {
    'BTC/USDT': 'BTC-USD',
    'ETH/USDT': 'ETH-USD', 
    'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD',
    'XRP/USDT': 'XRP-USD',
    'ADA/USDT': 'ADA-USD',
    'DOGE/USDT': 'DOGE-USD'
}

# ============================================
# 🪵 LOGGING SETUP - سیستم لاگ‌گیری
# ============================================

def setup_logging():
    """تنظیمات لاگ‌گیری"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    logger.addHandler(console_handler)
    
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    
    return logger

logger = setup_logging()

# ============================================
# 📊 TECHNICAL INDICATORS - اندیکاتورهای دستی
# ============================================

class TechnicalIndicators:
    """کلاس محاسبه اندیکاتورهای تکنیکال بدون pandas_ta"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """محاسبه RSI دستی"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
        """محاسبه EMA"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
        """محاسبه SMA"""
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """محاسبه ATR"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """محاسبه MACD"""
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        return pd.DataFrame({
            'MACD': macd,
            'Signal': signal_line,
            'Histogram': histogram
        })
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """محاسبه باندهای بولینگر"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return pd.DataFrame({
            'Upper': upper_band,
            'Middle': sma,
            'Lower': lower_band
        })

# ============================================
# 🗄️ DATABASE MANAGER - مدیریت دیتابیس
# ============================================

class DatabaseManager:
    """مدیریت دیتابیس ساده"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """ایجاد جداول دیتابیس"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    expiry REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY,
                    days INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            conn.commit()
        logger.info("✅ دیتابیس راه‌اندازی شد")
    
    def add_user(self, user_id: str, username: str = "", first_name: str = "", expiry: float = 0):
        """افزودن کاربر"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, expiry) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, expiry))
    
    def get_user(self, user_id: str):
        """دریافت کاربر"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            result = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", 
                (user_id,)
            ).fetchone()
            return dict(result) if result else None
    
    def create_license(self, days: int):
        """ایجاد لایسنس"""
        license_key = f"VIP-{uuid.uuid4().hex[:6].upper()}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO licenses (license_key, days) VALUES (?, ?)",
                (license_key, days)
            )
        return license_key
    
    def activate_license(self, license_key: str, user_id: str) -> Tuple[bool, str]:
        """فعال‌سازی لایسنس"""
        with sqlite3.connect(self.db_path) as conn:
            license_data = conn.execute(
                "SELECT days, is_active FROM licenses WHERE license_key = ?",
                (license_key,)
            ).fetchone()
            
            if not license_data:
                return False, "❌ لایسنس یافت نشد"
            
            if license_data[1] == 0:
                return False, "❌ لایسنس قبلاً استفاده شده"
            
            days = license_data[0]
            expiry = time.time() + (days * 86400)
            
            # غیرفعال کردن لایسنس
            conn.execute(
                "UPDATE licenses SET is_active = 0 WHERE license_key = ?",
                (license_key,)
            )
            
            # بروزرسانی کاربر
            self.add_user(user_id, expiry=expiry)
            conn.commit()
            
            expiry_date = datetime.fromtimestamp(expiry).strftime('%Y/%m/%d')
            return True, f"✅ اشتراک {days} روزه فعال شد!\n📅 انقضا: {expiry_date}"
    
    def get_all_users(self):
        """دریافت تمام کاربران"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM users").fetchall()
    
    def delete_user(self, user_id: str):
        """حذف کاربر"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

# ============================================
# 🧠 AI ANALYZER - تحلیلگر هوش مصنوعی
# ============================================

class AIAnalyzer:
    """تحلیلگر هوش مصنوعی"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        logger.info("🧠 تحلیلگر راه‌اندازی شد")
    
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """تحلیل یک نماد"""
        logger.info(f"🔍 تحلیل {symbol}")
        
        ticker = COIN_MAP.get(symbol)
        if not ticker:
            return None
        
        try:
            # دریافت داده
            df = yf.download(
                ticker,
                period=ANALYSIS_PERIOD,
                interval=ANALYSIS_TIMEFRAME,
                progress=False,
                timeout=10
            )
            
            if df.empty or len(df) < 20:
                return None
            
            # محاسبه اندیکاتورها
            close = df['Close']
            high = df['High']
            low = df['Low']
            
            # محاسبه اندیکاتورها
            rsi = self.indicators.calculate_rsi(close)
            ema_20 = self.indicators.calculate_ema(close, 20)
            ema_50 = self.indicators.calculate_ema(close, 50)
            ema_200 = self.indicators.calculate_ema(close, 200)
            atr = self.indicators.calculate_atr(high, low, close)
            
            # مقادیر آخرین کندل
            last_close = float(close.iloc[-1])
            last_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50
            last_atr = float(atr.iloc[-1]) if not atr.empty else last_close * 0.01
            last_ema_200 = float(ema_200.iloc[-1]) if not ema_200.empty else last_close
            
            # محاسبه امتیاز
            score = self._calculate_score(last_close, last_rsi, last_ema_200, last_atr)
            
            # محاسبه نقاط TP/SL
            if score >= 70:
                tp_multiplier = 3.0
                sl_multiplier = 1.6
            elif score >= 60:
                tp_multiplier = 2.5
                sl_multiplier = 1.4
            else:
                tp_multiplier = 2.0
                sl_multiplier = 1.2
            
            take_profit = last_close + (last_atr * tp_multiplier)
            stop_loss = max(last_close - (last_atr * sl_multiplier), last_close * 0.95)
            
            # تشخیص روند
            if last_close > last_ema_200:
                trend = "صعودی 📈"
            else:
                trend = "نزولی 📉"
            
            return {
                'symbol': symbol,
                'current_price': last_close,
                'win_probability': score,
                'take_profit': round(take_profit, 4),
                'stop_loss': round(stop_loss, 4),
                'rsi': last_rsi,
                'atr': last_atr,
                'trend': trend,
                'dataframe': df
            }
            
        except Exception as e:
            logger.error(f"❌ خطا در تحلیل {symbol}: {e}")
            return None
    
    def _calculate_score(self, price: float, rsi: float, ema_200: float, atr: float) -> float:
        """محاسبه امتیاز"""
        score = 50
        
        # تحلیل RSI
        if 45 < rsi < 65:
            score += 25
        elif 40 < rsi < 70:
            score += 15
        elif 35 < rsi < 75:
            score += 10
        
        # تحلیل روند
        if price > ema_200:
            score += 20
        
        # محدود کردن امتیاز
        return min(95, max(30, round(score, 1)))
    
    async def find_best_signal(self) -> Optional[Dict]:
        """یافتن بهترین سیگنال"""
        for symbol in list(COIN_MAP.keys())[:5]:
            analysis = await self.analyze_symbol(symbol)
            if analysis and analysis['win_probability'] >= MIN_WIN_RATE:
                return analysis
            await asyncio.sleep(0.5)
        return None
    
    async def create_chart(self, df: pd.DataFrame, symbol: str) -> Optional[io.BytesIO]:
        """ایجاد نمودار"""
        try:
            plt.style.use('dark_background')
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
            
            # نمودار قیمت
            ax1.plot(df.index, df['Close'], color='#00ff88', linewidth=2)
            ax1.set_title(f'{symbol} - Price Chart', color='white', fontsize=14)
            ax1.set_ylabel('Price', color='white')
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(colors='white')
            
            # نمودار RSI
            rsi = self.indicators.calculate_rsi(df['Close'])
            ax2.plot(df.index, rsi, color='#ff9900', linewidth=2)
            ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5)
            ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5)
            ax2.set_ylabel('RSI', color='white')
            ax2.set_ylim(0, 100)
            ax2.grid(True, alpha=0.3)
            ax2.tick_params(colors='white')
            
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, facecolor='#0a0a0a')
            buffer.seek(0)
            plt.close(fig)
            
            return buffer
            
        except Exception as e:
            logger.error(f"❌ خطا در ایجاد نمودار: {e}")
            return None

# ============================================
# 🤖 TRADING BOT - ربات اصلی
# ============================================

class TradingBot:
    """ربات تریدر"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.admin_id = str(ADMIN_ID)
        self.db = DatabaseManager(DB_PATH)
        self.analyzer = AIAnalyzer()
        self.app = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user = update.effective_user
        user_id = str(user.id)
        
        user_data = self.db.get_user(user_id)
        is_admin = user_id == self.admin_id
        has_access = is_admin or (user_data and user_data.get('expiry', 0) > time.time())
        
        if is_admin:
            keyboard = [['➕ ساخت لایسنس', '👥 کاربران'], ['💰 تحلیل ارز', '🔥 سیگنال']]
        elif has_access:
            keyboard = [['💰 تحلیل ارز', '🔥 سیگنال'], ['⏳ اعتبار من']]
        else:
            await update.message.reply_text("🔐 برای استفاده، لایسنس خود را وارد کنید:")
            return
        
        await update.message.reply_text(
            "🤖 به ربات تریدر خوش آمدید!",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام"""
        user = update.effective_user
        user_id = str(user.id)
        text = update.message.text
        
        user_data = self.db.get_user(user_id)
        is_admin = user_id == self.admin_id
        has_access = is_admin or (user_data and user_data.get('expiry', 0) > time.time())
        
        if text == '💰 تحلیل ارز':
            if has_access:
                await self.show_coins(update)
            else:
                await update.message.reply_text("❌ دسترسی ندارید!")
        
        elif text == '🔥 سیگنال':
            if has_access:
                await self.send_signal(update)
            else:
                await update.message.reply_text("❌ دسترسی ندارید!")
        
        elif text == '➕ ساخت لایسنس' and is_admin:
            license_key = self.db.create_license(30)
            await update.message.reply_text(f"✅ لایسنس ۳۰ روزه:\n`{license_key}`", parse_mode='Markdown')
        
        elif text == '👥 کاربران' and is_admin:
            await self.manage_users(update)
        
        elif text == '⏳ اعتبار من':
            if user_data:
                remaining = user_data['expiry'] - time.time()
                days = int(remaining // 86400)
                await update.message.reply_text(f"⏳ {days} روز باقی‌مانده")
            else:
                await update.message.reply_text("❌ کاربر یافت نشد")
        
        elif text.startswith('VIP-'):
            success, message = self.db.activate_license(text, user_id)
            await update.message.reply_text(message)
        
        elif not has_access:
            await update.message.reply_text("❌ دسترسی ندارید! لایسنس وارد کنید.")
    
    async def show_coins(self, update: Update):
        """نمایش لیست ارزها"""
        keyboard = []
        coins = list(COIN_MAP.keys())
        
        for i in range(0, len(coins), 2):
            row = []
            for j in range(2):
                if i + j < len(coins):
                    row.append(InlineKeyboardButton(coins[i + j], callback_data=coins[i + j]))
            keyboard.append(row)
        
        await update.message.reply_text(
            "🎯 انتخاب ارز:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def send_signal(self, update: Update):
        """ارسال سیگنال"""
        msg = await update.message.reply_text("🔍 در حال یافتن بهترین سیگنال...")
        
        signal = await self.analyzer.find_best_signal()
        
        if signal:
            chart = await self.analyzer.create_chart(signal['dataframe'], signal['symbol'])
            
            text = f"""
            🚀 **سیگنال ویژه**
            
            🪙 ارز: `{signal['symbol']}`
            💰 قیمت: `{signal['current_price']:,.2f}$`
            🎯 احتمال موفقیت: `{signal['win_probability']}%`
            📈 روند: {signal['trend']}
            
            🎯 TP: `{signal['take_profit']:,.2f}$`
            ⚠️ SL: `{signal['stop_loss']:,.2f}$`
            """
            
            if chart:
                await update.message.reply_photo(photo=chart, caption=text, parse_mode='Markdown')
            else:
                await update.message.reply_text(text, parse_mode='Markdown')
            
            await msg.delete()
        else:
            await msg.edit_text("❌ سیگنال با کیفیت یافت نشد")
    
    async def manage_users(self, update: Update):
        """مدیریت کاربران"""
        users = self.db.get_all_users()
        
        for user in users:
            expiry = user['expiry']
            if expiry > time.time():
                days = int((expiry - time.time()) // 86400)
                status = f"✅ فعال ({days} روز)"
            else:
                status = "❌ منقضی"
            
            keyboard = [[
                InlineKeyboardButton(f"🚫 حذف {user['first_name']}", 
                                   callback_data=f"del_{user['user_id']}")
            ]]
            
            text = f"👤 {user['first_name']}\n🆔 {user['user_id']}\n📊 {status}"
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کلیک"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data in COIN_MAP:
            user_id = str(query.from_user.id)
            user_data = self.db.get_user(user_id)
            is_admin = user_id == self.admin_id
            has_access = is_admin or (user_data and user_data.get('expiry', 0) > time.time())
            
            if not has_access:
                await query.edit_message_text("❌ دسترسی ندارید!")
                return
            
            await query.edit_message_text(f"🔍 تحلیل {data}...")
            
            analysis = await self.analyzer.analyze_symbol(data)
            
            if analysis:
                chart = await self.analyzer.create_chart(analysis['dataframe'], analysis['symbol'])
                
                text = f"""
                📊 تحلیل {analysis['symbol']}
                
                💰 قیمت: `{analysis['current_price']:,.2f}$`
                🎯 امتیاز: `{analysis['win_probability']}%`
                📈 روند: {analysis['trend']}
                
                🎯 TP: `{analysis['take_profit']:,.2f}$`
                ⚠️ SL: `{analysis['stop_loss']:,.2f}$`
                """
                
                if chart:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=chart,
                        caption=text,
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=text,
                        parse_mode='Markdown'
                    )
                
                await query.message.delete()
            else:
                await query.edit_message_text("❌ خطا در تحلیل!")
        
        elif data.startswith("del_"):
            if str(query.from_user.id) != self.admin_id:
                await query.edit_message_text("❌ شما ادمین نیستید!")
                return
            
            user_id = data.replace("del_", "")
            self.db.delete_user(user_id)
            await query.edit_message_text(f"✅ کاربر {user_id} حذف شد.")
    
    def setup_handlers(self):
        """تنظیم هندلرها"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def run(self):
        """اجرای ربات"""
        self.app = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        print("="*50)
        print("🤖 Trading Bot - Simple Version")
        print(f"👑 Admin: {ADMIN_ID}")
        print("="*50)
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        await asyncio.Event().wait()

# ============================================
# 🚀 MAIN EXECUTION
# ============================================

async def main():
    """تابع اصلی"""
    bot = TradingBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())