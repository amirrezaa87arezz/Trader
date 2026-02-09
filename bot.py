import os
import uuid
import time
import logging
import io
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import pymongo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- تنظیمات اصلی ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
MONGO_URI = "mongodb+srv://amirezarezvasi25_db_user:eixK3j5PuUq0wsdq@cluster0.on87bad.mongodb.net/?appName=Cluster0"

# --- اتصال به MongoDB ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db_mongo = client["TraderBotDB"]
    collection = db_mongo["MainData"]
    logging.info("✅ Connected to MongoDB Atlas!")
except Exception as e:
    logging.error(f"❌ Connection Error: {e}")

def get_db():
    data = collection.find_one({"_id": "global_storage"})
    if not data:
        data = {"_id": "global_storage", "active_licenses": {}, "user_access": {}}
        collection.insert_one(data)
    return data

def save_to_mongo(new_data):
    collection.replace_one({"_id": "global_storage"}, new_data)

# --- موتور تحلیل تکنیکال ---
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'NEAR/USDT': 'NEAR-USD',
    'PEPE/USDT': 'PEPE-USD', 'LINK/USDT': 'LINK-USD', 'AVAX/USDT': 'AVAX-USD'
}

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
        price = float(last['Close'])
        rsi = float(last['RSI'])
        atr = float(last['ATR'])
        
        score = 50
        if price > last['EMA_20']: score += 15
        if rsi < 35: score += 20
        if rsi > 65: score -= 20
        
        win_p = max(min(score, 98), 2)
        tp = price + (atr * 2.2)
        sl = price - (atr * 1.5)
        
        plt.figure(figsize=(10, 5))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc')
        plt.title(f"{symbol} AI Signal")
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
    db = get_db()
    
    if int(user_id) == ADMIN_ID:
        menu = [['➕ ساخت لایسنس', '📊 آمار کل'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
        await update.message.reply_text("👑 پنل مدیریت ابری فعال شد.", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
        return

    now = time.time()
    if user_id in db["user_access"] and db["user_access"][user_id] > now:
        menu = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنمای ترید مبتدی', '📊 وضعیت']]
        await update.message.reply_text("🚀 خوش آمدید!", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
    else:
        await update.message.reply_text("🔐 لایسنس خود را وارد کنید:", reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    db = get_db()

    if int(user_id) == ADMIN_ID:
        if text == '➕ ساخت لایسنس':
            await update.message.reply_text("تعداد روز اعتبار:")
            user_states[user_id] = 'wait'
            return
        elif user_states.get(user_id) == 'wait' and text.isdigit():
            key = f"VIP-{str(uuid.uuid4())[:8].upper()}"
            db["active_licenses"][key] = int(text)
            save_to_mongo(db)
            user_states[user_id] = None
            await update.message.reply_text(f"✅ لایسنس ابری:\n`{key}`", parse_mode='Markdown')
            return

    if text.startswith("VIP-"):
        if text in db["active_licenses"]:
            days = db["active_licenses"].pop(text)
            db["user_access"][user_id] = time.time() + (days * 86400)
            save_to_mongo(db)
            await update.message.reply_text(f"✅ فعال شد! {days} روز اشتراک برای شما ثبت شد.")
        return

    if user_id in db["user_access"] and db["user_access"][user_id] > time.time():
        if text == '💰 لیست ارزها':
            keys = list(COIN_MAP.keys())
            markup = InlineKeyboardMarkup([[InlineKeyboardButton(k, callback_data=k) for k in keys[i:i+2]] for i in range(0, len(keys), 2)])
            await update.message.reply_text("انتخاب ارز:", reply_markup=markup)
        elif text == '🎓 راهنمای ترید مبتدی':
            guide = (
                "📖 **چگونه ترید کنیم؟**\n\n"
                "1. ارزی با شانس بالای ۷۰٪ انتخاب کن.\n"
                "2. در صرافی، حد سود (TP) و حد ضرر (SL) را طبق ربات تنظیم کن.\n"
                "3. با اهرم (Leverage) پایین مثلاً 3x ترید کن.\n"
                "4. بیشتر از ۵٪ پولت را در یک معامله نگذار."
            )
            await update.message.reply_text(guide, parse_mode='Markdown')

async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    res, chart = analyze_logic(query.data)
    if res:
        cap = f"📊 **{res['symbol']}**\n🚀 شانس: `{res['win_p']}%` \n🎯 هدف: `{res['tp']:,.4f}`\n🛑 ضرر: `{res['sl']:,.4f}`"
        await context.bot.send_photo(update.effective_chat.id, chart, caption=cap, parse_mode='Markdown')

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_inline))
    app.run_polling()
