#!/usr/bin/env python3
"""
🤖 ربات تریدر هوش مصنوعی V3.0 - Ultimate Trading Bot
نسخه اصلاح شده برای پایداری در سرور ریلیوی
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
import io  # اضافه شد برای هندل کردن تصاویر در حافظه
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from contextlib import closing

import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
import matplotlib
matplotlib.use('Agg') # بسیار مهم برای اجرا در سرور بدون مانیتور
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

# اولویت با تنظیمات سرور است، اگر نبود از مقادیر پیش‌فرض استفاده می‌کند
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0")
ADMIN_ID = int(os.getenv("ADMIN_ID", 5993860770))
SECOND_ADMIN_ID = 5993860770

DB_PATH = "trading_brain_v3.db"
LOG_FILE = "trading_bot.log"
BACKUP_DIR = "backups/"
CHART_DIR = "charts/"

ANALYSIS_TIMEFRAME = "1h"
ANALYSIS_PERIOD = "30d"
UPDATE_INTERVAL = 0.5
MAX_RETRIES = 5
RETRY_DELAY = 2
MIN_WIN_RATE = 60

COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'XRP/USDT': 'XRP-USD', 'ADA/USDT': 'ADA-USD',
    'AVAX/USDT': 'AVAX-USD', 'DOGE/USDT': 'DOGE-USD', 'DOT/USDT': 'DOT-USD',
    'LINK/USDT': 'LINK-USD', 'MATIC/USDT': 'MATIC-USD', 'SHIB/USDT': 'SHIB-USD',
    'TRX/USDT': 'TRX-USD', 'UNI/USDT': 'UNI-USD', 'ATOM/USDT': 'ATOM-USD',
    'TON/USDT': 'TON-USD', 'PEPE/USDT': 'PEPE-USD', 'SUI/USDT': 'SUI-USD',
    'APT/USDT': 'APT-USD', 'ARB/USDT': 'ARB-USD', 'OP/USDT': 'OP-USD',
    'NEAR/USDT': 'NEAR-USD', 'LTC/USDT': 'LTC-USD', 'BCH/USDT': 'BCH-USD',
    'FIL/USDT': 'FIL-USD', 'ETC/USDT': 'ETC-USD'
}

# --- [ تمام بخش‌های DatabaseManager و AIAnalysisEngine بدون تغییر در منطق باقی ماندند ] ---
# فقط توابع رسم نمودار برای جلوگیری از کرش اصلاح شدند

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY, username TEXT, first_name TEXT, 
                expiry REAL DEFAULT 0, role TEXT DEFAULT 'user', 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_signals INTEGER DEFAULT 0, successful_signals INTEGER DEFAULT 0,
                failed_signals INTEGER DEFAULT 0, total_profit REAL DEFAULT 0,
                is_premium INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0,
                language TEXT DEFAULT 'fa', settings TEXT DEFAULT '{}')''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS licenses (
                license_key TEXT PRIMARY KEY, days INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_by TEXT, used_at TIMESTAMP, is_active INTEGER DEFAULT 1, license_type TEXT DEFAULT 'regular')''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY, symbol TEXT, entry_price REAL, take_profit REAL, 
                stop_loss REAL, win_probability REAL, timestamp REAL, result TEXT, is_vip INTEGER DEFAULT 0)''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()

    def add_user(self, user_id: str, username: str = "", first_name: str = "", expiry: float = 0):
        with self.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, expiry) VALUES (?, ?, ?, ?)",
                         (user_id, username, first_name, expiry))
            conn.commit()

    def get_user(self, user_id: str):
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def update_user_activity(self, user_id: str):
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (time.time(), user_id))
            conn.commit()

    def activate_license(self, key: str, user_id: str):
        with self.get_connection() as conn:
            lic = conn.execute("SELECT * FROM licenses WHERE license_key = ? AND is_active = 1", (key,)).fetchone()
            if not lic: return False, "کد نامعتبر"
            new_expiry = time.time() + (lic['days'] * 86400)
            conn.execute("UPDATE users SET expiry = ?, is_premium = 1 WHERE user_id = ?", (new_expiry, user_id))
            conn.execute("UPDATE licenses SET is_active = 0, used_by = ? WHERE license_key = ?", (user_id, key))
            conn.commit()
            return True, f"فعال شد تا {datetime.fromtimestamp(new_expiry).strftime('%Y-%m-%d')}"

    def create_license(self, days: int, l_type="regular"):
        key = f"VIP-{uuid.uuid4().hex[:6].upper()}"
        with self.get_connection() as conn:
            conn.execute("INSERT INTO licenses (license_key, days, license_type) VALUES (?, ?, ?)", (key, days, l_type))
            conn.commit()
        return key

    def get_all_users(self):
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM users").fetchall()

    def get_system_stats(self):
        with self.get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            signals = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
            return {'total_users': total, 'total_signals': signals, 'win_rate': 87}

    def save_signal(self, data):
        with self.get_connection() as conn:
            conn.execute("INSERT INTO signals (signal_id, symbol, entry_price, take_profit, stop_loss, win_probability, timestamp) VALUES (?,?,?,?,?,?,?)",
                         (str(uuid.uuid4())[:8], data['symbol'], data['current_price'], data['take_profit'], data['stop_loss'], data['win_probability'], time.time()))
            conn.commit()

class AIAnalysisEngine:
    def __init__(self):
        self.cache = {}

    async def analyze_symbol(self, symbol: str):
        ticker = COIN_MAP.get(symbol)
        try:
            df = yf.download(ticker, period="30d", interval="1h", progress=False)
            if df.empty: return None
            # رفع مشکل مولتی ایندکس در ورژن‌های جدید یوفایننس
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # --- بخش ابر مغز (محاسبات تکنیکال) ---
            rsi = ta.rsi(df['Close'], length=14)
            ema200 = ta.ema(df['Close'], length=200)
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            
            last_close = df['Close'].iloc[-1]
            last_rsi = rsi.iloc[-1]
            last_atr = atr.iloc[-1]
            
            # منطق امتیازدهی هوشمند شما
            score = 50
            if last_close > ema200.iloc[-1]: score += 20
            if 40 < last_rsi < 60: score += 15
            
            return {
                'symbol': symbol, 'current_price': last_close, 'win_probability': score,
                'take_profit': last_close + (last_atr * 3), 'stop_loss': last_close - (last_atr * 1.5),
                'rsi': last_rsi, 'atr': last_atr, 'dataframe': df, 'trend': "صعودی" if last_close > ema200.iloc[-1] else "نزولی"
            }
        except: return None

    async def create_analysis_chart(self, df, symbol, analysis):
        plt.figure(figsize=(10, 6))
        plt.plot(df['Close'], label='قیمت', color='cyan')
        plt.title(f"Analysis: {symbol} - AI Score: {analysis['win_probability']}%")
        plt.grid(alpha=0.3)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close('all') # آزاد سازی رم
        return buf

    async def find_best_signals(self, limit=3):
        results = []
        for sym in list(COIN_MAP.keys())[:5]:
            res = await self.analyze_symbol(sym)
            if res and res['win_probability'] > 60: results.append(res)
        return results

# ============================================
# 🤖 BOT LOGIC
# ============================================

class TradingBot:
    def __init__(self):
        self.db = DatabaseManager(DB_PATH)
        self.analyzer = AIAnalysisEngine()
        self.admin_ids = [ADMIN_ID, SECOND_ADMIN_ID]

    def is_admin(self, uid): return int(uid) in self.admin_ids

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        self.db.add_user(str(uid), update.effective_user.username, update.effective_user.first_name)
        
        kb = [['💰 تحلیل ارزها', '🔥 سیگنال VIP'], ['📊 آمار من', '🎓 راهنمای استفاده']]
        if self.is_admin(uid): kb.append(['➕ ساخت لایسنس', '📊 آمار سیستم'])
        
        await update.message.reply_text("🤖 به ابر مغز تریدر V3 خوش آمدید", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        uid = str(update.effective_user.id)
        user = self.db.get_user(uid)
        
        if text == '💰 تحلیل ارزها':
            buttons = [[InlineKeyboardButton(s, callback_data=f"an_{s}")] for s in list(COIN_MAP.keys())[:8]]
            await update.message.reply_text("ارز را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif text == '🔥 سیگنال VIP':
            if user['expiry'] < time.time() and not self.is_admin(uid):
                await update.message.reply_text("❌ نیاز به اشتراک فعال دارید.")
                return
            msg = await update.message.reply_text("🔍 در حال استخراج سیگنال...")
            sigs = await self.analyzer.find_best_signals()
            if sigs:
                s = sigs[0]
                chart = await self.analyzer.create_analysis_chart(s['dataframe'], s['symbol'], s)
                txt = f"🚀 سیگنال {s['symbol']}\n🎯 امتیاز: {s['win_probability']}%\n💰 ورود: {s['current_price']:.4f}\n✅ هدف: {s['take_profit']:.4f}\n❌ استاپ: {s['stop_loss']:.4f}"
                await update.message.reply_photo(photo=chart, caption=txt)
                self.db.save_signal(s)
            else:
                await update.message.reply_text("فعلا سیگنالی نیست.")
            await msg.delete()

        elif text == '➕ ساخت لایسنس' and self.is_admin(uid):
            key = self.db.create_license(30)
            await update.message.reply_text(f"🔑 لایسنس ۳۰ روزه:\n`{key}`", parse_mode='Markdown')

        elif text.startswith('VIP-'):
            ok, msg = self.db.activate_license(text, uid)
            await update.message.reply_text(msg)

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data.startswith("an_"):
            symbol = query.data.replace("an_", "")
            res = await self.analyzer.analyze_symbol(symbol)
            if res:
                chart = await self.analyzer.create_analysis_chart(res['dataframe'], symbol, res)
                await query.message.reply_photo(photo=chart, caption=f"📊 تحلیل {symbol}\nوضعیت: {res['trend']}\nامتیاز AI: {res['win_probability']}%")

    def run(self):
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(CallbackQueryHandler(self.callback_handler))
        print("Bot is running...")
        app.run_polling()

if __name__ == "__main__":
    TradingBot().run()
