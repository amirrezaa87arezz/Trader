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

# --- تنظیمات لاگ ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- تنظیمات اصلی ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
# لینک نهایی شما با پسورد اصلاح شده
MONGO_URI = "mongodb+srv://amirezarezvasi25_db_user:eixK3j5PuUq0wsdq@cluster0.on87bad.mongodb.net/?appName=Cluster0"

# --- اتصال به دیتابیس ابری ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db_mongo = client["TraderBotDB"]
    collection = db_mongo["MainData"]
    logging.info("✅ اتصال به دیتابیس ابری MongoDB برقرار شد!")
except Exception as e:
    logging.error(f"❌ خطای دیتابیس: {e}")

def get_db():
    data = collection.find_one({"_id": "global_storage"})
    if not data:
        data = {"_id": "global_storage", "active_licenses": {}, "user_access": {}}
        collection.insert_one(data)
    return data

def save_to_mongo(new_data):
    collection.replace_one({"_id": "global_storage"}, new_data)

# --- لیست ارزها ---
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'NEAR/USDT': 'NEAR-USD',
    'PEPE/USDT': 'PEPE-USD', 'LINK/USDT': 'LINK-USD', 'AVAX/USDT': 'AVAX-USD'
}

# --- موتور تحلیل پیشرفته ---
def analyze_logic(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        data = yf.download(ticker, period="7d", interval="1h", progress=False)
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # محاسبات تکنیکال برای دقت بالا
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI'])
        atr = float(last['ATR'])
        
        # سیستم امتیازدهی هوشمند
        score = 50
        if price > last['EMA_20']: score += 10 # روند صعودی کوتاه مدت
        if last['EMA_20'] > last['EMA_50']: score += 10 # تایید روند میان مدت
        if rsi < 32: score += 25 # اشباع فروش (فرصت خرید)
        if rsi > 68: score -= 25 # اشباع خرید (خطر ریزش)
        
        win_p = max(min(score, 98), 2)
        tp = price + (atr * 2.3) # هدف سود بر اساس نوسان بازار
        sl = price - (atr * 1.7) # حد ضرر منطقی
        
        # رسم نمودار حرفه‌ای
        plt.figure(figsize=(10, 5))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc', label='Price')
        plt.plot(df.index, df['EMA_20'], color='#ff9900', alpha=0.5, label='Trend')
        plt.fill_between(df.index, df['Close'], color='#00ffcc', alpha=0.1)
        plt.title(f"{symbol} AI Signal")
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return {'symbol': symbol, 'price': price, 'win_p': win_p, 'tp': tp, 'sl': sl}, buf
    except: return None, None

# --- هندلرهای ربات ---
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = get_db()
    
    if int(user_id) == ADMIN_ID:
        menu = [['➕ ساخت لایسنس', '📊 آمار کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
        await update.message.reply_text("💎 مدیریت خوش آمدید. دیتابیس ابری متصل است.", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
        return

    now = time.time()
    if user_id in db["user_access"] and db["user_access"][user_id] > now:
        menu = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنمای ترید مبتدی', '📊 وضعیت اشتراک']]
        await update.message.reply_text("🚀 دستیار هوشمند ترید آماده است!", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
    else:
        await update.message.reply_text("🔐 دسترسی شما محدود است.\nبرای استفاده از تحلیل‌ها، کد لایسنس خود را وارد کنید:", reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    db = get_db()

    # مدیریت ادمین
    if int(user_id) == ADMIN_ID:
        if text == '➕ ساخت لایسنس':
            await update.message.reply_text("مدت اعتبار (تعداد روز) را وارد کنید:")
            user_states[user_id] = 'wait_days'
            return
        elif user_states.get(user_id) == 'wait_days' and text.isdigit():
            key = f"VIP-{str(uuid.uuid4())[:8].upper()}"
            db["active_licenses"][key] = int(text)
            save_to_mongo(db)
            user_states[user_id] = None
            await update.message.reply_text(f"✅ لایسنس جدید ساخته شد:\n`{key}`", parse_mode='Markdown')
            return
        elif text == '📊 آمار کاربران':
            await update.message.reply_text(f"👥 تعداد کاربران فعال در دیتابیس: {len(db['user_access'])}")

    # فعالسازی لایسنس
    if text.startswith("VIP-"):
        if text in db["active_licenses"]:
            days = db["active_licenses"].pop(text)
            db["user_access"][user_id] = time.time() + (days * 86400)
            save_to_mongo(db)
            await update.message.reply_text(f"🎉 تبریک! اشتراک {days} روزه شما با موفقیت فعال شد. /start را بزنید.")
        else:
            await update.message.reply_text("❌ لایسنس اشتباه است یا قبلاً استفاده شده.")
        return

    # منوی کاربر
    if user_id in db["user_access"] and db["user_access"][user_id] > time.time():
        if text == '💰 لیست ارزها':
            keys = list(COIN_MAP.keys())
            markup = InlineKeyboardMarkup([[InlineKeyboardButton(k, callback_data=k) for k in keys[i:i+2]] for i in range(0, len(keys), 2)])
            await update.message.reply_text("ارز مورد نظر برای تحلیل زنده را انتخاب کنید:", reply_markup=markup)
        
        elif text == '🔥 پیشنهاد طلایی':
            msg = await update.message.reply_text("🔎 در حال اسکن بازار برای پیدا کردن بهترین فرصت...")
            best = None
            for s in COIN_MAP.keys():
                r, _ = analyze_logic(s)
                if r and (not best or r['win_p'] > best['win_p']): best = r
            
            if best:
                res, chart = analyze_logic(best['symbol'])
                cap = f"🏆 **بهترین پیشنهاد فعلی:** {res['symbol']}\n📈 شانس سود: `{res['win_p']}%`"
                await context.bot.send_photo(update.effective_chat.id, chart, caption=cap, parse_mode='Markdown')
            await msg.delete()

        elif text == '🎓 راهنمای ترید مبتدی':
            guide = (
                "📖 **چگونه با این ربات ترید کنیم؟ (ویژه مبتدی‌ها)**\n\n"
                "1️⃣ **انتخاب ارز:** ابتدا از لیست ارزها، موردی را انتخاب کن که شانس بالای ۷۵٪ دارد.\n\n"
                "2️⃣ **ورود به صرافی:** در صرافی (بخش Futures یا Spot)، قیمت فعلی را با 'قیمت ورود' ربات چک کن.\n\n"
                "3️⃣ **تنظیم سود و ضرر:** بلافاصله بعد از خرید، عدد **Take Profit** را برای خروج با سود و **Stop Loss** را برای جلوگیری از ضرر زیاد در صرافی ست کن.\n\n"
                "4️⃣ **قانون طلایی مدیریت سرمایه:** هرگز بیش از ۵٪ از کل پولت را وارد یک ترید نکن! (مثلاً اگر ۱۰۰ دلار داری، با ۵ دلار وارد شو).\n\n"
                "5️⃣ **اهرم (Leverage):** اگر مبتدی هستی، اهرم را از **3x** یا **5x** بالاتر نبر."
            )
            await update.message.reply_text(guide, parse_mode='Markdown')

async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("در حال تحلیل...")
    res, chart = analyze_logic(query.data)
    if res:
        cap = (f"📊 **تحلیل {res['symbol']}**\n\n"
               f"🚀 شانس موفقیت: `{res['win_p']}%` \n"
               f"💵 قیمت زنده: `{res['price']:,.4f}`\n"
               f"🎯 هدف سود (TP): `{res['tp']:,.4f}`\n"
               f"🛑 حد ضرر (SL): `{res['sl']:,.4f}`\n\n"
               f"⚠️ *نکته: سیگنال‌ها بر اساس هوش مصنوعی هستند، مدیریت سرمایه فراموش نشود.*")
        await context.bot.send_photo(update.effective_chat.id, chart, caption=cap, parse_mode='Markdown')

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_inline))
    app.run_polling()
    
