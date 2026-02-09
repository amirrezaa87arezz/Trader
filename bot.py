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

# تنظیمات لاگ برای عیب‌یابی در Railway
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- تنظیمات اصلی ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_FILE = "/tmp/database.json" # استفاده از پوشه tmp برای دسترسی بهتر در سرور

# --- مدیریت دیتابیس دائمی ---
def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"DB Load Error: {e}")
    return {"active_licenses": {}, "user_access": {}}

def save_db(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"DB Save Error: {e}")

db = load_db()
user_states = {}

COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'NEAR/USDT': 'NEAR-USD',
    'PEPE/USDT': 'PEPE-USD', 'LINK/USDT': 'LINK-USD', 'AVAX/USDT': 'AVAX-USD'
}

# --- توابع تحلیل و نمودار ---
def generate_chart(symbol, data):
    try:
        plt.figure(figsize=(10, 5))
        plt.style.use('dark_background')
        plt.plot(data.index, data['Close'], color='#00ffcc', linewidth=2)
        plt.fill_between(data.index, data['Close'], alpha=0.1, color='#00ffcc')
        plt.title(f"{symbol} Trend")
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        logging.error(f"Chart Error: {e}")
        return None

def analyze_logic(symbol, need_chart=True):
    try:
        ticker = COIN_MAP.get(symbol)
        data = yf.download(ticker, period="5d", interval="1h", progress=False)
        if data.empty: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI']) if not pd.isna(last['RSI']) else 50
        atr = float(last['ATR']) if not pd.isna(last['ATR']) else (price * 0.02)
        
        win_p = max(min(50 + (30-rsi if rsi<35 else rsi-70 if rsi>65 else 0), 95), 5)
        res = {
            'symbol': symbol, 'price': price, 'win_p': int(win_p),
            'tp': price + (atr * 2.5), 'sl': price - (atr * 1.5)
        }
        if need_chart:
            return res, generate_chart(symbol, df)
        return res
    except: return None

# --- هندلرهای تلگرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    logging.info(f"Start command from: {user_id}")

    if int(user_id) == ADMIN_ID:
        menu = [['➕ ساخت لایسنس', '📊 آمار کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
        await update.message.reply_text("💎 پنل مدیریت فعال شد:", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
        return

    now = time.time()
    if user_id in db["user_access"] and db["user_access"][user_id] > now:
        menu = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['📊 وضعیت اشتراک', '📊 راهنما']]
        await update.message.reply_text("🚀 خوش آمدید!", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
    else:
        await update.message.reply_text("🔐 دسترسی شما محدود است.\nلطفاً لایسنس خود را وارد کنید:", reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    now = time.time()

    # عملیات ادمین
    if int(user_id) == ADMIN_ID:
        if text == '➕ ساخت لایسنس':
            await update.message.reply_text("تعداد روز اعتبار (مثلاً 30):")
            user_states[user_id] = 'wait_days'
            return
        elif user_states.get(user_id) == 'wait_days' and text.isdigit():
            new_key = f"VIP-{str(uuid.uuid4())[:8].upper()}"
            db["active_licenses"][new_key] = int(text)
            save_db(db)
            user_states[user_id] = None
            await update.message.reply_text(f"✅ لایسنس ساخته شد:\n`{new_key}`", parse_mode='Markdown')
            return
        elif text == '📊 آمار کاربران':
            await update.message.reply_text(f"👥 کاربران فعال: {len(db['user_access'])}")

    # بررسی لایسنس کاربر
    if int(user_id) != ADMIN_ID and (user_id not in db["user_access"] or db["user_access"][user_id] < now):
        if text.startswith("VIP-"):
            if text in db["active_licenses"]:
                days = db["active_licenses"].pop(text)
                db["user_access"][user_id] = now + (days * 86400)
                save_db(db)
                await update.message.reply_text(f"✅ اکانت شما {days} روز فعال شد! /start را بزنید.")
            else:
                await update.message.reply_text("❌ لایسنس غلط یا استفاده شده.")
        return

    # منوی ترید
    if text == '💰 لیست ارزها':
        keys = list(COIN_MAP.keys())
        btn = [InlineKeyboardButton(k, callback_data=k) for k in keys]
        markup = InlineKeyboardMarkup([btn[i:i+2] for i in range(0, len(btn), 2)])
        await update.message.reply_text("ارز مورد نظر را انتخاب کنید:", reply_markup=markup)
    
    elif text == '🔥 پیشنهاد طلایی':
        wait = await update.message.reply_text("🔎 اسکن بازار...")
        best = None
        for s in COIN_MAP.keys():
            r = analyze_logic(s, False)
            if r and (not best or r['win_p'] > best['win_p']): best = r
        if best:
            res, chart = analyze_logic(best['symbol'], True)
            await context.bot.send_photo(update.effective_chat.id, chart, caption=f"🏆 بهترین فرصت: {best['symbol']}\nشانس: {best['win_p']}%")
        await wait.delete()

    elif text == '📊 راهنما':
        await update.message.reply_text("دستیار ترید هوشمند با استفاده از RSI و ATR نقاط ورود را محاسبه می‌کند.")

async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    if int(user_id) != ADMIN_ID and db["user_access"].get(user_id, 0) < time.time():
        await query.answer("اعتبار شما تمام شده!", show_alert=True)
        return
    
    await query.answer("در حال تحلیل...")
    res, chart = analyze_logic(query.data)
    if res and chart:
        cap = f"📊 **{res['symbol']}**\n🚀 شانس سود: `{res['win_p']}%` \n🎯 هدف: `{res['tp']:,.4f}`\n🛑 ضرر: `{res['sl']:,.4f}`"
        await context.bot.send_photo(update.effective_chat.id, chart, caption=cap, parse_mode='Markdown')

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_inline))
    app.run_polling()
        
