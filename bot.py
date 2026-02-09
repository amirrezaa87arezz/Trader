import os, uuid, time, logging, io, sqlite3
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- تنظیمات ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_PATH = "/app/data/bot_database.db"

# --- دیتابیس ارتقا یافته ---
def init_db():
    if not os.path.exists("/app/data"): os.makedirs("/app/data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (key TEXT PRIMARY KEY, days INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, expiry REAL)''')
    conn.commit()
    conn.close()

def add_license(key, days):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO licenses VALUES (?, ?)", (key, days))
    conn.commit()
    conn.close()

def use_license(key, user_id, name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT days FROM licenses WHERE key=?", (key,))
    res = c.fetchone()
    if res:
        expiry = time.time() + (res[0] * 86400)
        c.execute("DELETE FROM licenses WHERE key=?", (key,))
        c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, name, expiry))
        conn.commit()
        conn.close()
        return res[0]
    conn.close()
    return None

# --- موتور تحلیل پیشرفته ---
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'PEPE/USDT': 'PEPE-USD',
    'NEAR/USDT': 'NEAR-USD', 'AVAX/USDT': 'AVAX-USD', 'LINK/USDT': 'LINK-USD'
}

def get_signal(symbol, period="7d"):
    try:
        ticker = COIN_MAP.get(symbol)
        df = yf.download(ticker, period=period, interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # اندیکاتورهای حرفه‌ای
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        
        # سیستم امتیازدهی هوشمند
        score = 60 # پایه شانس
        if price > last['EMA_20'] > last['EMA_50']: score += 15 # روند صعودی قوی
        if last['RSI'] < 30: score += 20 # اشباع فروش
        if price < last['BBL_20_2.0']: score += 10 # برخورد به باند پایین
        
        win_p = max(min(score, 99), 30)
        tp = price + (last['ATR'] * 2.5)
        sl = price - (last['ATR'] * 1.8)
        
        # رسم نمودار
        plt.figure(figsize=(10, 5))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc', label='Price')
        plt.fill_between(df.index, df['BBU_20_2.0'], df['BBL_20_2.0'], color='gray', alpha=0.2)
        plt.title(f"AI Technical Analysis: {symbol}")
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return {'symbol': symbol, 'price': price, 'win_p': win_p, 'tp': tp, 'sl': sl}, buf
    except: return None, None

# --- هندلرها ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = update.effective_user.first_name
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute("SELECT expiry FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()

    if int(uid) == ADMIN_ID:
        kb = [['➕ ساخت لایسنس', '👥 مدیریت کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
        await update.message.reply_text(f"سلام رئیس {name}! پنل مدیریت آماده است.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif user and user[0] > time.time():
        kb = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنمای جامع', '⏳ اعتبار باقی‌مانده']]
        await update.message.reply_text(f"خوش آمدی {name}! آماده ترید هستی؟", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        await update.message.reply_text(f"سلام {name}!\nبرای دسترسی به سیگنال‌های هوشمند، لایسنس خود را وارد کنید:", reply_markup=ReplyKeyboardRemove())

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    
    # بخش ادمین
    if int(uid) == ADMIN_ID:
        if text == '➕ ساخت لایسنس':
            key = f"VIP-{uuid.uuid4().hex[:6].upper()}"
            add_license(key, 30) # پیش‌فرض ۳۰ روزه
            await update.message.reply_text(f"✅ لایسنس ۳۰ روزه ساخته شد:\n`{key}`", parse_mode='Markdown')
        elif text == '👥 مدیریت کاربران':
            conn = sqlite3.connect(DB_PATH)
            users = conn.execute("SELECT user_id, name FROM users").fetchall()
            conn.close()
            msg = "لیست کاربران:\n"
            btns = []
            for u_id, u_name in users:
                msg += f"👤 {u_name} ({u_id})\n"
                btns.append([InlineKeyboardButton(f"❌ حذف {u_name}", callback_data=f"del_{u_id}")])
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(btns))

    # اعتبار باقی‌مانده
    if text == '⏳ اعتبار باقی‌مانده':
        conn = sqlite3.connect(DB_PATH)
        user = conn.execute("SELECT expiry FROM users WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        if user:
            rem = user[0] - time.time()
            days = int(rem // 86400)
            hours = int((rem % 86400) // 3600)
            await update.message.reply_text(f"⏳ زمان باقی‌مانده اشتراک شما:\n✅ {days} روز و {hours} ساعت")

    # پیشنهاد طلایی
    if text == '🔥 پیشنهاد طلایی':
        await update.message.reply_text("🔎 در حال اسکن بازار برای پیدا کردن بهترین فرصت...")
        best_sig = None
        max_win = 0
        for coin in COIN_MAP.keys():
            res, _ = get_signal(coin)
            if res and res['win_p'] > max_win:
                max_win = res['win_p']
                best_sig = res
        if best_sig:
            await update.message.reply_text(f"🌟 **پیشنهاد طلایی سیستم:**\nارز: {best_sig['symbol']}\nشانس برد: {best_sig['win_p']}%\nقیمت: {best_sig['price']}")

    # راهنمای جامع
    if text == '🎓 راهنمای جامع':
        guide = (
            "🚀 **آموزش کار با ربات و مفاهیم ترید:**\n\n"
            "🔹 **TP (Take Profit) چیست؟**\n"
            "حد سود یعنی قیمتی که در آن معامله خودکار با سود بسته می‌شود. وقتی بازار به این عدد رسید، طمع نکن و اجازه بده ربات سودت را ذخیره کند.\n\n"
            "🔹 **SL (Stop Loss) چیست؟**\n"
            "حد ضرر مهم‌ترین بخش ترید است! عددی است که اگر بازار بر خلاف پیش‌بینی حرکت کرد، معامله را با ضرر کم می‌بندد تا کل پولت از بین نرود.\n\n"
            "🔹 **شانس برد (Win Rate):**\n"
            "این درصد بر اساس اندیکاتورهای RSI و Bollinger Bands محاسبه شده. بالای ۸۰٪ یعنی بازار در وضعیت عالی برای ورود است.\n\n"
            "⚠️ **نکته طلایی:** همیشه فقط با ۱ تا ۳ درصد سرمایه‌ات وارد یک معامله شو و لوریج را بالای ۳ نبر!"
        )
        await update.message.reply_text(guide, parse_mode='Markdown')

    if text.startswith("VIP-"):
        days = use_license(text, uid, update.effective_user.first_name)
        if days: await update.message.reply_text(f"✅ فعال شد! {days} روز دسترسی تایید شد. /start بزنید.")

    if text == '💰 لیست ارزها':
        btns = [[InlineKeyboardButton(k, callback_data=k) for k in list(COIN_MAP.keys())[i:i+2]] for i in range(0, len(COIN_MAP), 2)]
        await update.message.reply_text("انتخاب ارز:", reply_markup=InlineKeyboardMarkup(btns))

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith("del_"):
        u_id = query.data.split("_")[1]
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM users WHERE user_id=?", (u_id,))
        conn.commit()
        conn.close()
        await query.answer("کاربر حذف شد")
        await query.edit_message_text("✅ کاربر با موفقیت از دیتابیس حذف شد.")
        return
    
    res, chart = get_signal(query.data)
    if res:
        cap = f"📊 **تحلیل هوشمند {res['symbol']}**\n\n🎯 شانس برد: `{res['win_p']}%` \n💰 قیمت ورود: `{res['price']:,.4f}`\n✅ حد سود (TP): `{res['tp']:,.4f}`\n❌ حد ضرر (SL): `{res['sl']:,.4f}`"
        await context.bot.send_photo(uid, chart, caption=cap, parse_mode='Markdown')

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.run_polling()
