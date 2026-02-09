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

# تنظیمات لاگ برای مانیتورینگ در Railway
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- تنظیمات مدیریتی ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_FILE = "database.json"

# --- دیتابیس هوشمند و دائمی ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"active_licenses": {}, "user_access": {}, "settings": {"capital": 1000}}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

db = load_db()
user_states = {}

# لیست ارزهای تحت پوشش
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'NEAR/USDT': 'NEAR-USD',
    'PEPE/USDT': 'PEPE-USD', 'LINK/USDT': 'LINK-USD', 'AVAX/USDT': 'AVAX-USD'
}

# --- موتور تحلیل تکنیکال (دقت بالا) ---
def generate_chart(symbol, data):
    plt.figure(figsize=(12, 6))
    plt.style.use('dark_background')
    plt.plot(data.index, data['Close'], color='#00ffcc', linewidth=2, label='Price')
    plt.plot(data.index, data['EMA_20'], color='#ff9900', linestyle='--', alpha=0.7, label='EMA 20')
    plt.fill_between(data.index, data['Close'], alpha=0.1, color='#00ffcc')
    plt.title(f"{symbol} Real-time Analysis")
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def analyze_logic(symbol, need_chart=True):
    try:
        ticker = COIN_MAP.get(symbol)
        data = yf.download(ticker, period="14d", interval="1h", progress=False)
        if data.empty: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # اندیکاتورهای پیشرفته
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI'])
        atr = float(last['ATR'])
        
        # الگوریتم امتیازدهی به سیگنال
        score = 50
        if price > last['EMA_20']: score += 15
        if last['EMA_20'] > last['EMA_50']: score += 10
        if rsi < 30: score += 25  # اشباع فروش شدید
        if rsi > 70: score -= 25  # اشباع خرید شدید
        
        win_p = max(min(score, 98), 2)
        
        # محاسبه دقیق SL و TP بر اساس نوسان (ATR)
        tp = price + (atr * 2.5)
        sl = price - (atr * 1.5)
        profit_pct = ((tp - price) / price) * 100
        
        res = {
            'symbol': symbol, 'price': price, 'win_p': win_p,
            'tp': tp, 'sl': sl, 'profit_pct': profit_pct,
            'pos_size': (db["settings"]["capital"] * 0.02) / (abs(price - sl) / price)
        }
        
        if need_chart: return res, generate_chart(symbol, df)
        return res
    except Exception as e:
        logging.error(f"Analysis error for {symbol}: {e}")
        return None

# --- هندلرهای تلگرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if int(user_id) == ADMIN_ID:
        menu = [['➕ ساخت لایسنس', '📊 آمار کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['⚙️ تنظیمات']]
        await update.message.reply_text("👑 پنل مدیریت VIP فعال است.", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
    elif user_id in db["user_access"] and db["user_access"][user_id] > time.time():
        menu = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنمای مبتدی', '📊 وضعیت اشتراک']]
        await update.message.reply_text("🚀 دستیار ترید آماده است!", reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True))
    else:
        await update.message.reply_text("🔐 **دسترسی محدود!**\nلطفاً برای استفاده از ربات، کد لایسنس خود را وارد کنید:", reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    now = time.time()

    # عملیات مدیریت (Admin Only)
    if int(user_id) == ADMIN_ID:
        if text == '➕ ساخت لایسنس':
            await update.message.reply_text("مدت لایسنس (تعداد روز) را بفرستید:")
            user_states[user_id] = 'days'
            return
        elif user_states.get(user_id) == 'days' and text.isdigit():
            key = f"VIP-{str(uuid.uuid4())[:8].upper()}"
            db["active_licenses"][key] = int(text)
            save_db(db)
            user_states[user_id] = None
            await update.message.reply_text(f"✅ لایسنس جدید:\n`{key}`", parse_mode='Markdown')
            return

    # بررسی فعالسازی لایسنس
    if text.startswith("VIP-"):
        if text in db["active_licenses"]:
            days = db["active_licenses"].pop(text)
            db["user_access"][user_id] = now + (days * 86400)
            save_db(db)
            await update.message.reply_text(f"🎉 تبریک! دسترسی شما برای {days} روز فعال شد. /start را بزنید.")
            return

    # بررسی دسترسی عمومی
    if int(user_id) != ADMIN_ID and (user_id not in db["user_access"] or db["user_access"][user_id] < now):
        await update.message.reply_text("❌ لایسنس شما معتبر نیست.")
        return

    # منوی ترید و راهنما
    if text == '💰 لیست ارزها':
        keys = list(COIN_MAP.keys())
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(k, callback_data=k) for k in keys[i:i+2]] for i in range(0, len(keys), 2)])
        await update.message.reply_text("ارز مورد نظر برای تحلیل دقیق:", reply_markup=markup)
    
    elif text == '🔥 پیشنهاد طلایی':
        m = await update.message.reply_text("🔎 در حال اسکن کل بازار...")
        signals = []
        for s in COIN_MAP.keys():
            r = analyze_logic(s, False)
            if r: signals.append(r)
        
        best = max(signals, key=lambda x: x['win_p'])
        res, chart = analyze_logic(best['symbol'], True)
        await context.bot.send_photo(update.effective_chat.id, chart, 
            caption=f"🏆 **پیشنهاد طلایی:** {best['symbol']}\n📈 شانس سود: `{best['win_p']}%` \n💰 سود احتمالی: `{best['profit_pct']:.2f}%`", parse_mode='Markdown')
        await m.delete()

    elif text == '🎓 راهنمای مبتدی':
        guide = (
            "📖 **چطور ترید کنیم؟**\n\n"
            "1. وقتی ربات شانس بالای ۷۰٪ داد، یعنی موقعیت خوبی است.\n"
            "2. همیشه حد ضرر (SL) را در صرافی وارد کن تا پولت تمام نشود.\n"
            "3. برای شروع، لوریج یا اهرم صرافی را از **3x** بالاتر نبر.\n"
            "4. طبق 'حجم ورود' که ربات می‌گوید خرید کن."
        )
        await update.message.reply_text(guide, parse_mode='Markdown')

async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("در حال استخراج دیتای زنده...")
    res, chart = analyze_logic(query.data)
    if res:
        cap = (f"📊 **تحلیل {res['symbol']}**\n\n🚀 شانس موفقیت: `{res['win_p']}%` \n"
               f"💵 قیمت زنده: `{res['price']:,.2f}`\n🎯 هدف سود: `{res['tp']:,.2f}`\n"
               f"🛑 حد ضرر: `{res['sl']:,.2f}`\n💰 حجم پیشنهادی: `{res['pos_size']:,.1f}$`")
        await context.bot.send_photo(update.effective_chat.id, chart, caption=cap, parse_mode='Markdown')

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_inline))
    app.run_polling()
        
