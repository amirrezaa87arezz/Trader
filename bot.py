import os, uuid, time, logging, io, sqlite3
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- تنظیمات سیستمی ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_PATH = "/app/data/god_mode_v11.db"

logging.basicConfig(level=logging.INFO)

def init_db():
    if not os.path.exists("/app/data"): os.makedirs("/app/data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (key TEXT PRIMARY KEY, days INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, expiry REAL, role TEXT)''')
    conn.commit()
    conn.close()

# لیست ۳۰ ارز پرطرفدار
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'PEPE/USDT': 'PEPE-USD',
    'TON/USDT': 'TON11419-USD', 'SHIB/USDT': 'SHIB-USD', 'NEAR/USDT': 'NEAR-USD',
    'AVAX/USDT': 'AVAX-USD', 'SUI/USDT': 'SUI11840-USD', 'FET/USDT': 'FET-USD',
    'NOT/USDT': 'NOT-USD', 'WIF/USDT': 'WIF-USD', 'LINK/USDT': 'LINK-USD',
    'ARB/USDT': 'ARB11840-USD', 'XRP/USDT': 'XRP-USD', 'ADA/USDT': 'ADA-USD'
}

# --- موتور تحلیل فوق قدرتمند ---
def get_beast_signal(symbol, fast_scan=False):
    try:
        ticker = COIN_MAP.get(symbol)
        # برای اسکن طلایی دیتا کمتر میگیریم که سریع باشه
        period = "5d" if fast_scan else "10d"
        df = yf.download(ticker, period=period, interval="1h", progress=False, timeout=10)
        
        if df.empty or len(df) < 20: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # اندیکاتورهای حرفه‌ای
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        
        # استراتژی نوسان‌گیری (Win Rate High)
        score = 60
        if price > last['EMA_200']: score += 20 # تایید روند صعودی
        if last['RSI'] < 35: score += 15 # اشباع فروش
        if price < last['BBL_20_2.0']: score += 10 # برخورد به باند پایین
        
        win_p = max(min(score, 98), 35)
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        tp = price + (atr * 2.5)
        sl = price - (atr * 1.5)

        if fast_scan: return {'symbol': symbol, 'win_p': win_p, 'price': price}, None

        plt.clf()
        plt.figure(figsize=(10, 5))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc', linewidth=2)
        plt.fill_between(df.index, df['BBU_20_2.0'], df['BBL_20_2.0'], alpha=0.1, color='cyan')
        plt.title(f"AI POWER ANALYSIS: {symbol}")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close('all')
        
        return {'symbol': symbol, 'price': price, 'win_p': win_p, 'tp': tp, 'sl': sl}, buf
    except: return None, None

# --- هندلرها ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute("SELECT expiry, role FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()

    is_admin = int(uid) == ADMIN_ID or (user and user[1] == 'admin')
    if is_admin:
        kb = [['➕ ساخت لایسنس', '👥 مدیریت کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
    elif user and user[0] > time.time():
        kb = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنمای جامع', '⏳ اعتبار باقی‌مانده']]
    else:
        await update.message.reply_text("🔐 لطفاً لایسنس VIP خود را وارد کنید:")
        return

    await update.message.reply_text("💎 به قدرتمندترین ربات تحلیلگر خوش آمدید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)

    # بخش پیشنهاد طلایی (اصلاح شده و سریع)
    if 'پیشنهاد طلایی' in text:
        m = await update.message.reply_text("🎯 در حال شکار بهترین فرصت بازار (اسکن هوشمند)...")
        best = None
        # اسکن سریع فقط روی ۵ ارز برتر بازار برای جلوگیری از هنگ
        for c in ['BTC/USDT', 'SOL/USDT', 'PEPE/USDT', 'ETH/USDT', 'TON/USDT']:
            res, _ = get_beast_signal(c, fast_scan=True)
            if res and (not best or res['win_p'] > best['win_p']):
                best = res
        
        if best:
            await m.edit_text(f"🌟 **پیشنهاد طلایی پیدا شد:**\n\n🪙 ارز: {best['symbol']}\n📈 شانس برد: `{best['win_p']}%` \n💰 قیمت: `{best['price']:,.4f}`\n\nبرای دریافت چارت و حد ضرر، از 'لیست ارزها' انتخابش کنید.")
        else:
            await m.edit_text("⚠️ بازار در حال حاضر سیگنال قطعی ندارد. کمی بعد تلاش کنید.")
        return

    # مدیریت کاربران
    if 'مدیریت کاربران' in text and int(uid) == ADMIN_ID:
        conn = sqlite3.connect(DB_PATH); users = conn.execute("SELECT user_id, name FROM users").fetchall(); conn.close()
        if not users: await update.message.reply_text("کاربری یافت نشد."); return
        btns = [[InlineKeyboardButton(f"❌ حذف {u[1]}", callback_data=f"del_{u[0]}")] for u in users]
        await update.message.reply_text("👥 لیست کاربران فعال:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if 'ساخت لایسنس' in text and int(uid) == ADMIN_ID:
        k = f"VIP-{uuid.uuid4().hex[:6].upper()}"
        conn = sqlite3.connect(DB_PATH); conn.execute("INSERT INTO licenses VALUES (?, ?)", (k, 30)); conn.commit(); conn.close()
        await update.message.reply_text(f"✅ لایسنس جدید:\n`{k}`", parse_mode='Markdown')
        return

    if 'لیست ارزها' in text:
        keys = list(COIN_MAP.keys())
        btns = [[InlineKeyboardButton(keys[i], callback_data=keys[i]), InlineKeyboardButton(keys[i+1], callback_data=keys[i+1])] for i in range(0, len(keys)-1, 2)]
        await update.message.reply_text("ارز مورد نظر را برای تحلیل عمیق انتخاب کنید:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if text.startswith("VIP-"):
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        res = c.execute("SELECT days FROM licenses WHERE key=?", (text,)).fetchone()
        if res:
            exp = time.time() + (res[0] * 86400)
            c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (uid, update.effective_user.first_name, exp, 'user'))
            c.execute("DELETE FROM licenses WHERE key=?", (text,))
            conn.commit(); await update.message.reply_text("✅ اشتراک فعال شد! /start بزنید.")
        else: await update.message.reply_text("❌ لایسنس اشتباه.")
        conn.close()

async def callback_worker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith("del_"):
        uid = query.data.split("_")[1]
        conn = sqlite3.connect(DB_PATH); conn.execute("DELETE FROM users WHERE user_id=?", (uid,)); conn.commit(); conn.close()
        await query.edit_message_text("✅ کاربر حذف شد.")
        return

    await query.answer("🚀 در حال تحلیل سنگین...")
    res, chart = get_beast_signal(query.data)
    if res:
        cap = f"📊 **تحلیل فوق حرفه‌ای {res['symbol']}**\n\n🎯 شانس برد: `{res['win_p']}%` \n💵 قیمت ورود: `{res['price']:,.4f}`\n\n✅ حد سود (TP): `{res['tp']:,.4f}`\n❌ حد ضرر (SL): `{res['sl']:,.4f}`"
        await context.bot.send_photo(query.message.chat_id, chart, caption=cap, parse_mode='Markdown')
    else:
        await query.message.reply_text("❌ خطا در اتصال به صرافی. دوباره تلاش کنید.")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(callback_worker))
    app.run_polling()
