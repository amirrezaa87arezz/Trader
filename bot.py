import os, uuid, time, logging, io, sqlite3
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# تنظیمات اصلی
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_PATH = "/app/data/bot_v6.db"

# لاگ برای عیب‌یابی سریع
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

def init_db():
    if not os.path.exists("/app/data"): os.makedirs("/app/data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (key TEXT PRIMARY KEY, days INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, expiry REAL, role TEXT)''')
    conn.commit()
    conn.close()

COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'PEPE/USDT': 'PEPE-USD',
    'TON/USDT': 'TON11419-USD', 'SHIB/USDT': 'SHIB-USD', 'NEAR/USDT': 'NEAR-USD'
}

# --- تحلیلگر فوق حرفه‌ای ---
def get_advanced_signal(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        df = yf.download(ticker, period="7d", interval="1h", progress=False)
        if df.empty: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # اندیکاتورهای ترکیبی
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        
        # محاسبه امتیاز هوشمند (AI Score)
        score = 65
        if price > last['EMA_20']: score += 10
        if price > last['EMA_200']: score += 15
        if last['RSI'] < 30: score += 15
        if last['RSI'] > 70: score -= 20
        
        win_p = max(min(score, 99), 35)
        tp = price + (last['ATR'] * 2.5)
        sl = price - (last['ATR'] * 1.8)

        # ساخت نمودار
        plt.clf()
        plt.figure(figsize=(10, 5))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc', linewidth=2)
        plt.title(f"AI Advanced Scan: {symbol}")
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return {'symbol': symbol, 'price': price, 'win_p': win_p, 'tp': tp, 'sl': sl}, buf
    except Exception as e:
        logging.error(f"Error: {e}")
        return None, None

# --- هندلرهای تلگرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = update.effective_user.first_name
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute("SELECT expiry, role FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()

    is_admin = int(uid) == ADMIN_ID or (user and user[1] == 'admin')

    if is_admin:
        kb = [['➕ ساخت لایسنس', '👥 مدیریت کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
        await update.message.reply_text(f"💎 پنل مدیریت فعال شد.\nسلام رئیس {name}!", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif user and user[0] > time.time():
        kb = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنمای جامع', '⏳ اعتبار باقی‌مانده']]
        await update.message.reply_text(f"🚀 خوش آمدی {name}!", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        await update.message.reply_text(f"سلام {name}!\nبرای ورود به دنیای سیگنال‌های VIP، لایسنس خود را وارد کنید:")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    
    # کنترل لایسنس
    if text.startswith("VIP-"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        res = c.execute("SELECT days FROM licenses WHERE key=?", (text,)).fetchone()
        if res:
            exp = time.time() + (res[0] * 86400)
            c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (uid, update.effective_user.first_name, exp, 'user'))
            c.execute("DELETE FROM licenses WHERE key=?", (text,))
            conn.commit()
            await update.message.reply_text("✅ اشتراک فعال شد! /start را بزنید.")
        else:
            await update.message.reply_text("❌ لایسنس نامعتبر.")
        conn.close()
        return

    # مدیریت کاربران (فقط ادمین)
    if text == '👥 مدیریت کاربران' and int(uid) == ADMIN_ID:
        conn = sqlite3.connect(DB_PATH)
        users = conn.execute("SELECT user_id, name FROM users").fetchall()
        conn.close()
        if not users:
            await update.message.reply_text("کاربری یافت نشد.")
            return
        btns = [[InlineKeyboardButton(f"👤 {u[1]} ({u[0]})", callback_data=f"user_{u[0]}")] for u in users]
        await update.message.reply_text("یک کاربر را برای مدیریت انتخاب کنید:", reply_markup=InlineKeyboardMarkup(btns))
        return

    # پیشنهاد طلایی
    if text == '🔥 پیشنهاد طلایی':
        m = await update.message.reply_text("💎 در حال شکار بهترین موقعیت بازار...")
        # اسکن سریع
        best = None
        for c in list(COIN_MAP.keys())[:5]:
            res, _ = get_advanced_signal(c)
            if res and (not best or res['win_p'] > best['win_p']): best = res
        if best:
            await m.edit_text(f"🌟 **سیگنال طلایی پیدا شد:**\n\nارز: {best['symbol']}\nشانس: `{best['win_p']}%` \nقیمت: `{best['price']:,.4f}`", parse_mode='Markdown')

    if text == '➕ ساخت لایسنس' and int(uid) == ADMIN_ID:
        k = f"VIP-{uuid.uuid4().hex[:6].upper()}"
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO licenses VALUES (?, ?)", (k, 30))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ لایسنس ساخته شد:\n`{k}`", parse_mode='Markdown')

    if text == '💰 لیست ارزها':
        btns = [[InlineKeyboardButton(k, callback_data=k) for k in list(COIN_MAP.keys())[i:i+2]] for i in range(0, len(COIN_MAP), 2)]
        await update.message.reply_text("ارز مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(btns))

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    # منوی مدیریت کاربر
    if data.startswith("user_"):
        uid = data.split("_")[1]
        btns = [
            [InlineKeyboardButton("❌ حذف کاربر", callback_data=f"del_{uid}")],
            [InlineKeyboardButton("👑 ادمین کردن", callback_data=f"makeadm_{uid}")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="back_manage")]
        ]
        await query.edit_message_text(f"مدیریت کاربر آیدی: `{uid}`", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
        return

    if data.startswith("del_"):
        uid = data.split("_")[1]
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM users WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()
        await query.answer("حذف شد.")
        await query.edit_message_text("✅ کاربر با موفقیت حذف شد.")
        return

    if data.startswith("makeadm_"):
        uid = data.split("_")[1]
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE users SET role='admin' WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()
        await query.answer("ادمین شد.")
        await query.edit_message_text("✅ کاربر به سطح دسترسی ادمین ارتقا یافت.")
        return

    # بخش تحلیل ارز (بدون خطا)
    await query.answer("🔎 تحلیلگر هوشمند در حال کار است...")
    res, chart = get_advanced_signal(data)
    if res:
        cap = f"📊 **تحلیل {res['symbol']}**\n\n🎯 شانس برد: `{res['win_p']}%` \n💰 قیمت: `{res['price']:,.4f}`\n✅ حد سود: `{res['tp']:,.4f}`\n❌ حد ضرر: `{res['sl']:,.4f}`"
        await context.bot.send_photo(query.message.chat_id, chart, caption=cap, parse_mode='Markdown')
    else:
        await query.message.reply_text("❌ خطا در دریافت داده‌ها. دوباره تلاش کنید.")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.run_polling()
