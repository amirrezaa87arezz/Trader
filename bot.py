import os
import uuid
import time
import logging
import io
import sqlite3
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- تنظیمات لاگ ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- تنظیمات اصلی (توکن و آیدی ادمین) ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_PATH = "/app/data/bot_database.db"  # مسیر متصل به Volume ریلی‌وی

# --- مدیریت دیتابیس داخلی (SQLite) ---
def init_db():
    # ساخت پوشه data اگر وجود نداشته باشد
    if not os.path.exists("/app/data"):
        os.makedirs("/app/data")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # جدول لایسنس‌های استفاده نشده
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (key TEXT PRIMARY KEY, days INTEGER)''')
    # جدول کاربرانی که لایسنس فعال کرده‌اند
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, expiry REAL)''')
    conn.commit()
    conn.close()

def add_license(key, days):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO licenses VALUES (?, ?)", (key, days))
    conn.commit()
    conn.close()

def use_license(key, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT days FROM licenses WHERE key=?", (key,))
    res = c.fetchone()
    if res:
        days = res[0]
        expiry = time.time() + (days * 86400)
        c.execute("DELETE FROM licenses WHERE key=?", (key,))
        c.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, expiry))
        conn.commit()
        conn.close()
        return days
    conn.close()
    return None

def check_access(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT expiry FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    if res and res[0] > time.time():
        return True
    return False

# --- لیست ارزها ---
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'NEAR/USDT': 'NEAR-USD',
    'PEPE/USDT': 'PEPE-USD', 'AVAX/USDT': 'AVAX-USD', 'LINK/USDT': 'LINK-USD'
}

# --- موتور تحلیل هوشمند ---
def analyze_logic(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        data = yf.download(ticker, period="7d", interval="1h", progress=False)
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price, rsi, atr = float(last['Close']), float(last['RSI']), float(last['ATR'])
        
        score = 50
        if price > float(last['EMA_20']): score += 15
        if rsi < 35: score += 20
        if rsi > 65: score -= 20
        
        win_p = max(min(score, 98), 2)
        tp = price + (atr * 2.2)
        sl = price - (atr * 1.5)
        
        plt.figure(figsize=(10, 5))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc', label='Price')
        plt.title(f"{symbol} AI Signal")
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return {'symbol': symbol, 'price': price, 'win_p': win_p, 'tp': tp, 'sl': sl}, buf
    except: return None, None

# --- هندلرهای تلگرام ---
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if int(user_id) == ADMIN_ID:
        menu = [['➕ ساخت لایسنس', '📊 آمار کاربران'], ['💰 لیست ارزها', '🎓 راهنما']]
        await update.message.reply_text("💎 مدیر عزیز خوش آمدید.\nسیستم ذخیره‌سازی Volume فعال است.", 
                                       reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
        return

    if check_access(user_id):
        menu = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنما', '⏳ اعتبار باقی‌مانده']]
        await update.message.reply_text("🚀 دستیار ترید آماده است!", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
    else:
        await update.message.reply_text("🔐 برای استفاده از ربات، لطفاً لایسنس خود را وارد کنید (شروع با -VIP):", 
                                       reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    # بخش ادمین
    if int(user_id) == ADMIN_ID:
        if text == '➕ ساخت لایسنس':
            await update.message.reply_text("مدت اعتبار لایسنس را به عدد (روز) وارد کنید:")
            user_states[user_id] = 'waiting_days'
            return
        elif user_states.get(user_id) == 'waiting_days' and text.isdigit():
            new_key = f"VIP-{uuid.uuid4().hex[:8].upper()}"
            add_license(new_key, int(text))
            user_states[user_id] = None
            await update.message.reply_text(f"✅ لایسنس ساخته شد:\n\n`{new_key}`\n\nاعتبار: {text} روز", parse_mode='Markdown')
            return

    # فعال‌سازی لایسنس
    if text.startswith("VIP-"):
        days = use_license(text, user_id)
        if days:
            await update.message.reply_text(f"✅ لایسنس با موفقیت فعال شد!\nمدت: {days} روز\nحالا /start را بزنید.")
        else:
            await update.message.reply_text("❌ لایسنس اشتباه است یا قبلاً استفاده شده.")
        return

    # منوی کاربری (فقط برای افراد دارای دسترسی)
    if check_access(user_id):
        if text == '💰 لیست ارزها':
            keys = list(COIN_MAP.keys())
            markup = InlineKeyboardMarkup([[InlineKeyboardButton(k, callback_data=k) for k in keys[i:i+2]] for i in range(0, len(keys), 2)])
            await update.message.reply_text("جفت‌ارز مورد نظر برای تحلیل AI را انتخاب کنید:", reply_markup=markup)
        elif text == '🎓 راهنما':
            await update.message.reply_text("1. ارز را انتخاب کن.\n2. طبق TP و SL ربات خرید بزن.\n3. لوریج را روی 3x بگذار.")

async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("در حال تحلیل...")
    res, chart = analyze_logic(query.data)
    if res:
        cap = f"📊 **سیگنال {res['symbol']}**\n\n🚀 احتمال برد: `{res['win_p']}%` \n💵 قیمت فعلی: `{res['price']:,.4f}`\n🎯 حد سود (TP): `{res['tp']:,.4f}`\n🛑 حد ضرر (SL): `{res['sl']:,.4f}`"
        await context.bot.send_photo(update.effective_chat.id, chart, caption=cap, parse_mode='Markdown')

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_inline))
    app.run_polling()
