import os, uuid, time, logging, io, sqlite3, asyncio, json, math, hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup, 
                     ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, 
                         ContextTypes, MessageHandler, filters)

# ============================================
# ⚠️ WARNING: TOKENS ARE EMBEDDED IN CODE
# ============================================

# --- توکن و تنظیمات ادمین (در کد سخت‌کد شده) ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
SECOND_ADMIN_ID = 5993860770  # ادمین دوم (مشابه اول)

# --- تنظیمات سیستم ---
DB_PATH = "trading_brain_v2.db"
LOG_FILE = "trading_bot.log"
BACKUP_DIR = "backups/"

# --- تنظیمات تحلیل ---
ANALYSIS_TIMEFRAME = "1h"
ANALYSIS_PERIOD = "30d"
MAX_RETRIES = 3
RETRY_DELAY = 2

# --- تنظیمات ریسک ---
RISK_PER_TRADE = 0.02  # 2% ریسک در هر معامله
MIN_WIN_RATE = 60      # حداقل 60% برای سیگنال
MAX_SIGNALS_PER_DAY = 10

# --- نقشه ارزها (اضافه شده ارزهای بیشتر) ---
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
    'NEAR/USDT': 'NEAR-USD'
}

# --- تنظیمات لاگ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# 🧠 سیستم دیتابیس پیشرفته
# ============================================

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """ایجاد اتصال به دیتابیس"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """ایجاد جداول دیتابیس"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # جدول کاربران
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    expiry REAL,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_signals INTEGER DEFAULT 0,
                    successful_signals INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0
                )
            ''')
            
            # جدول لایسنس‌ها
            c.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY,
                    days INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_by TEXT,
                    used_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (used_by) REFERENCES users(user_id)
                )
            ''')
            
            # جدول سیگنال‌ها
            c.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    entry_price REAL,
                    take_profit REAL,
                    stop_loss REAL,
                    win_probability REAL,
                    timestamp REAL,
                    generated_by TEXT,
                    is_vip INTEGER DEFAULT 0,
                    result TEXT,
                    closed_at TIMESTAMP
                )
            ''')
            
            # جدول لاگ فعالیت‌ها
            c.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    action TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول تنظیمات
            c.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ایجاد ایندکس‌ها برای عملکرد بهتر
            c.execute('CREATE INDEX IF NOT EXISTS idx_users_expiry ON users(expiry)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_id)')
            
            conn.commit()
    
    def log_activity(self, user_id: str, action: str, details: str = ""):
        """ثبت فعالیت کاربر"""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                (user_id, action, details)
            )
            conn.commit()
    
    def add_user(self, user_id: str, username: str, first_name: str, last_name: str, expiry: float, role: str = 'user'):
        """اضافه کردن کاربر جدید"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, expiry, role, last_active) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, expiry, role, time.time()))
            conn.commit()
            self.log_activity(user_id, "REGISTER", f"User registered with expiry: {expiry}")
    
    def get_user(self, user_id: str):
        """دریافت اطلاعات کاربر"""
        with self.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?", 
                (user_id,)
            ).fetchone()
    
    def update_user_activity(self, user_id: str):
        """بروزرسانی زمان آخرین فعالیت"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (time.time(), user_id)
            )
            conn.commit()
    
    def create_license(self, days: int) -> str:
        """ایجاد لایسنس جدید"""
        license_key = f"VIP-{uuid.uuid4().hex[:8].upper()}-{datetime.now().strftime('%m%d')}"
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO licenses (license_key, days) VALUES (?, ?)",
                (license_key, days)
            )
            conn.commit()
            self.log_activity("SYSTEM", "CREATE_LICENSE", f"Created {days}-day license: {license_key}")
        return license_key
    
    def activate_license(self, license_key: str, user_id: str) -> Tuple[bool, str]:
        """فعال‌سازی لایسنس"""
        with self.get_connection() as conn:
            license_data = conn.execute(
                "SELECT days, is_active FROM licenses WHERE license_key = ?",
                (license_key,)
            ).fetchone()
            
            if not license_data:
                return False, "لایسنس یافت نشد"
            
            if license_data['is_active'] == 0:
                return False, "لایسنس قبلاً استفاده شده"
            
            days = license_data['days']
            expiry = time.time() + (days * 86400)
            
            # غیرفعال کردن لایسنس
            conn.execute(
                "UPDATE licenses SET used_by = ?, used_at = ?, is_active = 0 WHERE license_key = ?",
                (user_id, datetime.now().isoformat(), license_key)
            )
            
            # بروزرسانی کاربر
            user = self.get_user(user_id)
            if user:
                current_expiry = user['expiry'] or 0
                if current_expiry > time.time():
                    expiry = current_expiry + (days * 86400)
            
            conn.execute(
                "INSERT OR REPLACE INTO users (user_id, expiry, last_active) VALUES (?, ?, ?)",
                (user_id, expiry, time.time())
            )
            
            conn.commit()
            self.log_activity(user_id, "ACTIVATE_LICENSE", f"Activated {days}-day license")
            return True, f"لایسنس {days} روزه با موفقیت فعال شد!"
    
    def get_all_users(self):
        """دریافت تمام کاربران"""
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    
    def delete_user(self, user_id: str):
        """حذف کاربر"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            self.log_activity("ADMIN", "DELETE_USER", f"Deleted user: {user_id}")
    
    def get_system_stats(self):
        """دریافت آمار سیستم"""
        with self.get_connection() as conn:
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active_users = conn.execute("SELECT COUNT(*) FROM users WHERE expiry > ?", 
                                      (time.time(),)).fetchone()[0]
            total_licenses = conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
            active_licenses = conn.execute("SELECT COUNT(*) FROM licenses WHERE is_active = 1").fetchone()[0]
            total_signals = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_licenses': total_licenses,
                'active_licenses': active_licenses,
                'total_signals': total_signals
            }
    
    def save_signal(self, signal_data: Dict):
        """ذخیره سیگنال"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO signals 
                (signal_id, symbol, entry_price, take_profit, stop_loss, 
                 win_probability, timestamp, generated_by, is_vip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data.get('signal_id', str(uuid.uuid4())),
                signal_data['symbol'],
                signal_data['entry_price'],
                signal_data['take_profit'],
                signal_data['stop_loss'],
                signal_data['win_probability'],
                time.time(),
                signal_data.get('generated_by', 'BOT'),
                signal_data.get('is_vip', 0)
            ))
            conn.commit()

# ============================================
# 🧠 موتور تحلیل هوش مصنوعی
# ============================================

class AIAnalysisEngine:
    def __init__(self):
        self.indicators_cache = {}
    
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """تحلیل پیشرفته ارز"""
        logger.info(f"تحلیل ارز: {symbol}")
        
        ticker = COIN_MAP.get(symbol)
        if not ticker:
            logger.error(f"نماد {symbol} پشتیبانی نمی‌شود")
            return None
        
        # تلاش برای دریافت داده
        for attempt in range(MAX_RETRIES):
            try:
                df = yf.download(
                    ticker, 
                    period=ANALYSIS_PERIOD, 
                    interval=ANALYSIS_TIMEFRAME, 
                    progress=False, 
                    timeout=15
                )
                
                if df.empty or len(df) < 100:
                    logger.warning(f"داده‌های ناکافی برای {symbol}")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                
                # پردازش داده‌ها
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                # محاسبه اندیکاتورهای پیشرفته
                analysis = await self._calculate_advanced_indicators(df, symbol)
                
                if analysis['win_probability'] >= MIN_WIN_RATE:
                    logger.info(f"سیگنال قوی برای {symbol}: {analysis['win_probability']}%")
                
                return analysis
                
            except Exception as e:
                logger.error(f"خطا در تحلیل {symbol} (تلاش {attempt+1}): {e}")
                await asyncio.sleep(RETRY_DELAY)
        
        logger.error(f"تحلیل {symbol} پس از {MAX_RETRIES} تلاش ناموفق بود")
        return None
    
    async def _calculate_advanced_indicators(self, df: pd.DataFrame, symbol: str) -> Dict:
        """محاسبه اندیکاتورهای پیشرفته"""
        try:
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']
            
            # ۱. اندیکاتورهای روند
            ema_20 = ta.ema(close, length=20)
            ema_50 = ta.ema(close, length=50)
            ema_200 = ta.ema(close, length=200)
            sma_50 = ta.sma(close, length=50)
            
            # ۲. اندیکاتورهای مومنتوم
            rsi = ta.rsi(close, length=14)
            macd = ta.macd(close)
            stoch = ta.stoch(high, low, close)
            mfi = ta.mfi(high, low, close, volume, length=14)
            
            # ۳. اندیکاتورهای نوسان
            bb = ta.bbands(close, length=20, std=2)
            atr = ta.atr(high, low, close, length=14)
            
            # ۴. اندیکاتورهای حجم
            obv = ta.obv(close, volume)
            vwap = ta.vwap(high, low, close, volume)
            
            # ۵. اندیکاتورهای سفارشی
            adx = ta.adx(high, low, close, length=14)
            ichimoku = ta.ichimoku(high, low, close)
            
            # محاسبه آخرین مقادیر
            last_close = float(close.iloc[-1])
            last_rsi = float(rsi.iloc[-1])
            last_mfi = float(mfi.iloc[-1])
            last_atr = float(atr.iloc[-1])
            last_ema_200 = float(ema_200.iloc[-1])
            
            # محاسبه امتیاز هوش مصنوعی
            ai_score = self._calculate_ai_score({
                'close': last_close,
                'rsi': last_rsi,
                'mfi': last_mfi,
                'atr': last_atr,
                'ema_200': last_ema_200,
                'ema_50': float(ema_50.iloc[-1]),
                'sma_50': float(sma_50.iloc[-1]),
                'volume': float(volume.iloc[-1]),
                'bb_upper': float(bb.iloc[-1, 0]),
                'bb_lower': float(bb.iloc[-1, 2]),
                'adx': float(adx.iloc[-1, 0]),
                'macd': float(macd.iloc[-1, 0]),
                'stoch_k': float(stoch.iloc[-1, 0])
            })
            
            # تعیین نوع سیگنال
            if ai_score >= 80:
                signal_type = "🟢 قوی"
                tp_multiplier = 3.5
                sl_multiplier = 1.8
            elif ai_score >= 65:
                signal_type = "🟡 متوسط"
                tp_multiplier = 2.8
                sl_multiplier = 1.5
            else:
                signal_type = "🔴 ضعیف"
                tp_multiplier = 2.0
                sl_multiplier = 1.2
            
            # محاسبه حد سود و ضرر
            take_profit = last_close + (last_atr * tp_multiplier)
            stop_loss = last_close - (last_atr * sl_multiplier)
            
            # اطمینان از منطقی بودن مقادیر
            if stop_loss <= 0:
                stop_loss = last_close * 0.95
            
            return {
                'symbol': symbol,
                'current_price': last_close,
                'win_probability': ai_score,
                'take_profit': round(take_profit, 4),
                'stop_loss': round(stop_loss, 4),
                'signal_type': signal_type,
                'risk_reward_ratio': round((take_profit - last_close) / (last_close - stop_loss), 2),
                'atr': last_atr,
                'rsi': last_rsi,
                'mfi': last_mfi,
                'trend': "صعودی" if last_close > last_ema_200 else "نزولی",
                'timestamp': time.time(),
                'dataframe': df,
                'indicators': {
                    'ema_20': float(ema_20.iloc[-1]),
                    'ema_50': float(ema_50.iloc[-1]),
                    'ema_200': last_ema_200,
                    'bb_upper': float(bb.iloc[-1, 0]),
                    'bb_lower': float(bb.iloc[-1, 2])
                }
            }
            
        except Exception as e:
            logger.error(f"خطا در محاسبه اندیکاتورها: {e}")
            return None
    
    def _calculate_ai_score(self, indicators: Dict) -> float:
        """محاسبه امتیاز هوش مصنوعی (0-100)"""
        score = 0
        
        # ۱. قدرت روند (25 امتیاز)
        if indicators['close'] > indicators['ema_200']:
            score += 15
        if indicators['close'] > indicators['ema_50']:
            score += 10
        
        # ۲. اندیکاتور مومنتوم (25 امتیاز)
        if 45 < indicators['rsi'] < 65:
            score += 15
        elif 40 < indicators['rsi'] < 70:
            score += 10
        elif 35 < indicators['rsi'] < 75:
            score += 5
        
        if indicators['mfi'] > 60:
            score += 10
        
        # ۳. موقعیت در کانال بولینگر (20 امتیاز)
        bb_position = (indicators['close'] - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
        if 0.3 < bb_position < 0.7:
            score += 20
        elif 0.2 < bb_position < 0.8:
            score += 10
        
        # ۴. حجم و قدرت خرید (15 امتیاز)
        if indicators['volume'] > 0:
            score += min(15, indicators['volume'] / 1000000)
        
        # ۵. واگرایی و همگرایی (15 امتیاز)
        if indicators['macd'] > 0:
            score += 10
        if indicators['adx'] > 25:
            score += 5
        
        # ۶. Stochastic (اضافه‌کردن در صورت وجود)
        if 'stoch_k' in indicators and 20 < indicators['stoch_k'] < 80:
            score += 10
        
        # محدود کردن امتیاز به 100
        return min(100, max(20, score))
    
    async def find_best_signals(self, limit: int = 5) -> List[Dict]:
        """یافتن بهترین سیگنال‌های بازار"""
        logger.info("جستجوی بهترین سیگنال‌های بازار...")
        
        best_signals = []
        symbols_to_analyze = list(COIN_MAP.keys())[:10]  # تحلیل 10 ارز اول
        
        for symbol in symbols_to_analyze:
            analysis = await self.analyze_symbol(symbol)
            if analysis and analysis['win_probability'] >= 70:
                best_signals.append(analysis)
            
            if len(best_signals) >= limit:
                break
            
            # تاخیر برای جلوگیری از محدودیت API
            await asyncio.sleep(1)
        
        # مرتب‌سازی بر اساس امتیاز
        best_signals.sort(key=lambda x: x['win_probability'], reverse=True)
        return best_signals

# ============================================
# 🤖 کلاس اصلی ربات
# ============================================

class TradingBot:
    def __init__(sel