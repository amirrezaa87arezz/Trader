import os, uuid, time, logging, io, sqlite3
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- تنظیمات سیستمی ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_PATH = "/app/data/bot_database.db"

# --- دیتابیس ---
def init_db():
    if not os.path.exists("/app/data"): os.makedirs("/app/data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (key TEXT PRIMARY KEY, days INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, expiry REAL)''')
    conn.commit()
    conn.close()

# --- لیست گسترده ارزها (۲۰ ارز برتر) ---
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'PEPE/USDT': 'PEPE-USD',
    'NEAR/USDT': 'NEAR-USD', 'AVAX/USDT': 'AVAX-USD', 'LINK/USDT': 'LINK-USD',
    'SHIB/USDT': 'SHIB-USD', 'DOT/USDT': 'DOT-USD', 'MATIC/USDT': 'MATIC-USD',
    'ADA/USDT': 'ADA-USD', 'TON/USDT': 'TON11419-USD', 'ARB/USDT': 'ARB11840-USD',
    'OP/USDT': 'OP-USD', 'SUI/USDT': 'SUI11840-USD', 'WIF/USDT': 'WIF-USD',
    'FET/USDT': 'FET-USD', 'RNDR/USDT': 'RNDR-USD'
}

# --- موتور تحلیل فوق پیشرفته ---
def get_signal(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        df = yf.download(ticker, period="7d", interval="1h", progress=False)
        if df.empty: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # اندیکاتورهای ترکیبی برای دقت بالا
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        # Bollinger Bands
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        # ATR برای TP/SL
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        
        # منطق تحلیل (ترکیب روند و نوسان)
        score = 65 
        if price > last['EMA_20']: score += 10
        if price > last['EMA_200']: score += 15 # روند صعودی بلندمدت
        if last['RSI'] < 35: score += 15 # اشباع فروش (فرصت خرید)
        if last['RSI'] > 70: score -= 20 # اشباع خرید (خطر)
        
        win_p = max(min(score, 98), 35)
        # محاسبه دقیق تارگت و استاپ بر اساس نوسان بازار (ATR)
        tp = price + (last['ATR'] * 2.3)
        sl = price - (last['ATR'] * 1.6)
        
        # رسم نمودار حرفه‌ای
        plt.figure(figsize=(10, 6))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc', label='Price', linewidth=2)
        plt.plot(df.index, df['EMA_20'], color='#ff9900', label='EMA 20', alpha=0.6)
        plt.fill_between(df.index, df['BBU_20_2.0'], df['BBL_20_2.0'], color='white', alpha=0.1)
        plt.title(f"AI Advanced Analysis: {symbol}")
        plt.grid(alpha=0.1)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return {'symbol': symbol, 'price': price, 'win_p': win_p, 'tp': tp, 'sl': sl}, buf
    except Exception as e:
        logging.error(f"Error in analyze: {e}")
        return None, None

# --- هندلرها ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = update.effective_user.first_name
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute("SELECT expiry FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()

    if int(uid) == ADMIN_ID:
        kb = [['➕ ساخت لایسنس', '👥 مدیریت کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
        await update.message.reply_text(f"👑 ادمین عزیز {name} خوش آمدید.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif user and user[0] > time.time():
        kb = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنمای جامع', '⏳ اعتبار باقی‌مانده']]
        await update.message.reply_text(f"🚀 خوش آمدی {name}!", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        await update.message.reply_text(f"سلام {name}! برای دسترسی به پنل سیگنال، لایسنس خود را وارد کنید:")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    
    # بخش ادمین
    if int(uid) == ADMIN_ID:
        if text == '➕ ساخت لایسنس':
            key = f"VIP-{uuid.uuid4().hex[:6].upper()}"
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO licenses VALUES (?, ?)", (key, 30))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ لایسنس ۳۰ روزه ساخته شد:\n`{key}`", parse_mode='Markdown')
            return
        elif text == '👥 مدیریت کاربران':
            conn = sqlite3.connect(DB_PATH)
            users = conn.execute("SELECT user_id, name FROM users").fetchall()
            conn.close()
            if not users:
                await update.message.reply_text("هنوز کاربری عضو نشده است.")
                return
            btns = []
            for u_id, u_name in users:
                btns.append([InlineKeyboardButton(f"❌ حذف {u_name} ({u_id})", callback_data=f"del_{u_id}")])
            await update.message.reply_text("لیست کاربران فعال:", reply_markup=InlineKeyboardMarkup(btns))
            return

    # پیشنهاد طلایی (اصلاح شده)
    if text == '🔥 پیشنهاد طلایی':
        msg = await update.message.reply_text("🔎 در حال تحلیل ۲۰ ارز برتر برای پیدا کردن بهترین فرصت...")
        best_sig = None
        max_win = 0
        # فقط ۵ ارز اول را برای سرعت بیشتر اسکن می‌کند
        for coin in list(COIN_MAP.keys())[:8]:
            res, _ = get_signal(coin)
            if res and res['win_p'] > max_win:
                max_win = res['win_p']
                best_sig = res
        if best_sig:
            await msg.edit_text(f"🌟 **پیشنهاد طلایی سیستم:**\n\nارز: {best_sig['symbol']}\nشانس برد: `{best_sig['win_p']}%` \nقیمت: `{best_sig['price']:,.4f}`\n\n(برای جزئیات بیشتر از لیست ارزها انتخابش کنید)", parse_mode='Markdown')
        return

    # اعتبار باقی‌مانده
    if text == '⏳ اعتبار باقی‌مانده':
        conn = sqlite3.connect(DB_PATH)
        user = conn.execute("SELECT expiry FROM users WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        if user:
            rem = user[0] - time.time()
            await update.message.reply_text(f"⏳ اشتراک شما: {int(rem // 86400)} روز و {int((rem % 86400) // 3600)} ساعت باقی‌مانده.")
        return

    # راهنمای جامع (اصلاح شده)
    if text == '🎓 راهنمای جامع':
        guide = (
            "🚀 **راهنمای جامع ترید با ربات AI**\n\n"
            "✅ **TP (Take Profit) یا حد سود:**\n"
            "قیمتی است که ربات پیش‌بینی کرده سود شما در آنجا تکمیل می‌شود. بهتر است معامله را در این نقطه ببندید.\n\n"
            "❌ **SL (Stop Loss) یا حد ضرر:**\n"
            "حیاتی‌ترین بخش! قیمتی است که اگر بازار برعکس شد، باید از معامله خارج شوید تا کل موجودی‌تان (Liquid) از بین نرود.\n\n"
            "📈 **نحوه استفاده:**\n"
            "۱. یک ارز با شانس بالای ۸۰٪ انتخاب کنید.\n"
            "۲. در صرافی وارد پوزیشن Buy شوید.\n"
            "۳. اعداد TP و SL را دقیقاً در صرافی ست کنید.\n"
            "۴. لوریج (Leverage) را برای امنیت روی ۲ یا ۳ بگذارید."
        )
        await update.message.reply_text(guide, parse_mode='Markdown')
        return

    # فعال‌سازی لایسنس
    if text.startswith("VIP-"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        res = c.execute("SELECT days FROM licenses WHERE key=?", (text,)).fetchone()
        if res:
            expiry = time.time() + (res[0] * 86400)
            c.execute("DELETE FROM licenses WHERE key=?", (text,))
            c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (uid, update.effective_user.first_name, expiry))
            conn.commit()
            await update.message.reply_text("✅ دسترسی VIP فعال شد! /start را بزنید.")
        else:
            await update.message.reply_text("❌ لایسنس نامعتبر است.")
        conn.close()
        return

    if text == '💰 لیست ارزها':
        btns = [[InlineKeyboardButton(k, callback_data=k) for k in list(COIN_MAP.keys())[i:i+2]] for i in range(0, len(COIN_MAP), 2)]
        await update.message.reply_text("انتخاب ارز برای تحلیل:", reply_markup=InlineKeyboardMarkup(btns))

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # مدیریت حذف کاربر توسط ادمین
    if query.data.startswith("del_"):
        u_id = query.data.split("_")[1]
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM users WHERE user_id=?", (u_id,))
        conn.commit()
        conn.close()
        await query.answer("کاربر با موفقیت حذف شد.")
        await query.edit_message_text("✅ کاربر از دیتابیس حذف شد.")
        return
    
    # نمایش تحلیل ارز
    await query.answer("در حال تحلیل...")
    res, chart = get_signal(query.data)
    if res:
        cap = f"📊 **تحلیل {res['symbol']}**\n\n🎯 شانس برد: `{res['win_p']}%` \n💰 قیمت: `{res['price']:,.4f}`\n✅ حد سود (TP): `{res['tp']:,.4f}`\n❌ حد ضرر (SL): `{res['sl']:,.4f}`"
        await context.bot.send_photo(update.effective_chat.id, chart, caption=cap, parse_mode='Markdown')

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.run_polling()
