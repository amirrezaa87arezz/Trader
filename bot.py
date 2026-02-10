import os
import sqlite3
import time
import uuid
import asyncio
import logging
from datetime import datetime

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ========== تنظیمات ==========
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770

# مسیر دیتابیس در Railway
DB_PATH = "/data/trading_bot.db" if os.path.exists("/data") else "trading_bot.db"

# لیست ارزها
COIN_MAP = {
    'BTC/USDT': 'BTC-USD',
    'ETH/USDT': 'ETH-USD',
    'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD',
    'XRP/USDT': 'XRP-USD'
}

# ========== لاگ‌گیری ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== دیتابیس ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (key TEXT PRIMARY KEY, days INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, expiry REAL)''')
    conn.commit()
    conn.close()
    logger.info("✅ دیتابیس راه‌اندازی شد")

# ========== تحلیل ==========
async def analyze_coin(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        df = yf.download(ticker, period="7d", interval="1h", progress=False)
        
        if df.empty:
            return None
        
        # تحلیل ساده
        close = df['Close']
        rsi = ta.rsi(close, length=14).iloc[-1]
        ema_20 = ta.ema(close, length=20).iloc[-1]
        
        price = float(close.iloc[-1])
        
        # امتیازدهی ساده
        score = 50
        if 40 < rsi < 70:
            score += 20
        if price > ema_20:
            score += 15
        
        score = min(95, max(30, score))
        
        return {
            'symbol': symbol,
            'price': price,
            'score': score,
            'rsi': rsi,
            'df': df
        }
    except Exception as e:
        logger.error(f"خطا در تحلیل: {e}")
        return None

# ========== دستورات ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    conn = sqlite3.connect(DB_PATH)
    user_data = conn.execute("SELECT expiry FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    
    is_admin = user_id == str(ADMIN_ID)
    
    if is_admin:
        keyboard = [['➕ ساخت لایسنس', '👥 کاربران'], ['📊 تحلیل ارز']]
    elif user_data and user_data[0] > time.time():
        keyboard = [['📊 تحلیل ارز', '⏳ اعتبار من']]
    else:
        await update.message.reply_text("🔐 برای استفاده، لایسنس خود را وارد کنید:")
        return
    
    await update.message.reply_text(
        "🤖 به ربات تریدر خوش آمدید!\nلطفاً گزینه مورد نظر را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    text = update.message.text
    
    # بررسی دسترسی
    conn = sqlite3.connect(DB_PATH)
    user_data = conn.execute("SELECT expiry FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    
    is_admin = user_id == str(ADMIN_ID)
    has_access = is_admin or (user_data and user_data[0] > time.time())
    
    if text == '📊 تحلیل ارز':
        if has_access:
            buttons = []
            for coin in COIN_MAP.keys():
                buttons.append([InlineKeyboardButton(coin, callback_data=coin)])
            
            await update.message.reply_text(
                "🎯 انتخاب ارز:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await update.message.reply_text("❌ دسترسی ندارید!")
    
    elif text == '➕ ساخت لایسنس' and is_admin:
        key = f"VIP-{uuid.uuid4().hex[:6].upper()}"
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO licenses VALUES (?, ?)", (key, 30))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ لایسنس ۳۰ روزه:\n`{key}`", parse_mode='Markdown')
    
    elif text == '👥 کاربران' and is_admin:
        conn = sqlite3.connect(DB_PATH)
        users = conn.execute("SELECT user_id, name FROM users").fetchall()
        conn.close()
        
        if users:
            for u in users:
                await update.message.reply_text(f"👤 {u[1]}\n🆔 {u[0]}")
        else:
            await update.message.reply_text("👥 کاربری یافت نشد")
    
    elif text == '⏳ اعتبار من':
        if user_data:
            remaining = user_data[0] - time.time()
            days = int(remaining // 86400)
            await update.message.reply_text(f"⏳ {days} روز باقی‌مانده")
        else:
            await update.message.reply_text("❌ کاربر یافت نشد")
    
    elif text.startswith('VIP-'):
        conn = sqlite3.connect(DB_PATH)
        license_data = conn.execute("SELECT days FROM licenses WHERE key=?", (text,)).fetchone()
        
        if license_data:
            expiry = time.time() + (license_data[0] * 86400)
            conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", 
                        (user_id, user.first_name, expiry))
            conn.execute("DELETE FROM licenses WHERE key=?", (text,))
            conn.commit()
            await update.message.reply_text("✅ لایسنس فعال شد! /start بزنید.")
        else:
            await update.message.reply_text("❌ لایسنس نامعتبر")
        conn.close()
    
    elif not has_access:
        await update.message.reply_text("❌ دسترسی ندارید! لایسنس وارد کنید.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    analysis = await analyze_coin(query.data)
    
    if analysis:
        # ایجاد نمودار ساده
        plt.figure(figsize=(10, 4))
        plt.plot(analysis['df'].index, analysis['df']['Close'], color='green')
        plt.title(f"{analysis['symbol']} - Price Chart")
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()
        
        caption = f"📊 {analysis['symbol']}\n💰 قیمت: {analysis['price']:,.2f}\n🎯 امتیاز: {analysis['score']}%\n📈 RSI: {analysis['rsi']:.1f}"
        
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=buffer,
            caption=caption
        )
    else:
        await query.message.reply_text("❌ خطا در تحلیل")

# ========== اصلی ==========
def main():
    init_db()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("🤖 ربات در حال راه‌اندازی...")
    app.run_polling()

if __name__ == "__main__":
    main()