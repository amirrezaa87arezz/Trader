import os
import json
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import io, asyncio, logging, uuid, time
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- تنظیمات اصلی ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_FILE = "database.json"

# --- مدیریت دیتابیس ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"active_licenses": {}, "user_access": {}}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

db = load_db()

COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'NEAR/USDT': 'NEAR-USD',
    'PEPE/USDT': 'PEPE-USD', 'LINK/USDT': 'LINK-USD', 'AVAX/USDT': 'AVAX-USD'
}

# --- توابع تحلیل (نسخه بهینه) ---
def analyze_logic(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        data = yf.download(ticker, period="5d", interval="1h", progress=False)
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        last = df.iloc[-1]
        price, rsi, atr = float(last['Close']), float(last['RSI']), float(last['ATR'])
        win_p = max(min(50 + (30-rsi if rsi<35 else rsi-70 if rsi>65 else 0), 95), 5)
        tp, sl = price + (atr * 2.5), price - (atr * 1.5)
        return {'symbol': symbol, 'price': price, 'win_p': int(win_p), 'tp': tp, 'sl': sl}
    except: return None

# --- هندلرهای اصلی ---
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if int(user_id) == ADMIN_ID:
        admin_menu = [['➕ ساخت لایسنس', '📊 آمار کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
        await update.message.reply_text("👑 مدیر عزیز خوش آمدید!\nبرای ساخت لایسنس از دکمه زیر استفاده کنید:", 
                                       reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
        return

    now = time.time()
    if user_id in db["user_access"] and db["user_access"][user_id] > now:
        expiry_date = datetime.fromtimestamp(db["user_access"][user_id]).strftime('%Y-%m-%d')
        main_menu = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['📊 وضعیت اشتراک']]
        await update.message.reply_text(f"✅ اشتراک شما فعال است.\n📅 انقضا: {expiry_date}", 
                                       reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
    else:
        await update.message.reply_text("🔐 **دسترسی محدود!**\nلطفاً کد لایسنس خریداری شده را وارد کنید:", 
                                       reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    # مدیریت پنل ادمین
    if int(user_id) == ADMIN_ID:
        if text == '➕ ساخت لایسنس':
            await update.message.reply_text("مدت زمان اعتبار (به روز) را وارد کنید:")
            user_states[user_id] = 'awaiting_days'
            return
        
        if user_states.get(user_id) == 'awaiting_days':
            if text.isdigit():
                days = int(text)
                new_key = f"VIP-{str(uuid.uuid4())[:8].upper()}"
                db["active_licenses"][new_key] = days
                save_db(db)
                await update.message.reply_text(f"✅ لایسنس ساخته شد:\n\n`{new_key}`\n\nمدت: {days} روز", parse_mode='Markdown')
                user_states[user_id] = None
            return
        
        if text == '📊 آمار کاربران':
            count = len(db["user_access"])
            await update.message.reply_text(f"👥 تعداد کاربران تایید شده: {count}")

    # بررسی لایسنس برای کاربران
    now = time.time()
    if user_id not in db["user_access"] or db["user_access"][user_id] < now:
        if text.startswith("VIP-"):
            if text in db["active_licenses"]:
                days = db["active_licenses"].pop(text)
                db["user_access"][user_id] = now + (days * 86400)
                save_db(db)
                await update.message.reply_text("🎉 فعالسازی با موفقیت انجام شد! برای استفاده /start بزنید.")
            else:
                await update.message.reply_text("❌ کد لایسنس نامعتبر یا استفاده شده است.")
            return

    # منوی ترید (برای کاربران دارای اشتراک)
    if text == '💰 لیست ارزها':
        keys = list(COIN_MAP.keys())
        keyboard = [keys[i:i+2] for i in range(0, len(keys), 2)]
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(c, callback_data=c) for c in row] for row in keyboard])
        await update.message.reply_text("ارز را انتخاب کنید:", reply_markup=markup)

    elif text == '📊 وضعیت اشتراک':
        expiry = datetime.fromtimestamp(db["user_access"][user_id]).strftime('%Y-%m-%d %H:%M')
        await update.message.reply_text(f"⏳ اشتراک شما تا تاریخ زیر معتبر است:\n`{expiry}`", parse_mode='Markdown')

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_inline)) # تابع handle_inline مشابه قبل
    app.run_polling()
