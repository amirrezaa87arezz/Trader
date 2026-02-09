import os, uuid, time, logging, io, sqlite3, asyncio
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

COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'PEPE/USDT': 'PEPE-USD',
    'NEAR/USDT': 'NEAR-USD', 'AVAX/USDT': 'AVAX-USD', 'LINK/USDT': 'LINK-USD',
    'SHIB/USDT': 'SHIB-USD', 'DOT/USDT': 'DOT-USD', 'MATIC/USDT': 'MATIC-USD',
    'ADA/USDT': 'ADA-USD', 'TON/USDT': 'TON11419-USD', 'ARB/USDT': 'ARB11840-USD',
    'OP/USDT': 'OP-USD', 'SUI/USDT': 'SUI11840-USD', 'WIF/USDT': 'WIF-USD',
    'FET/USDT': 'FET-USD', 'RNDR/USDT': 'RNDR-USD'
}

# --- موتور تحلیل پیشرفته ---
def get_signal(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        data = yf.download(ticker, period="5d", interval="1h", progress=False)
        if data.empty: return None, None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        
        score = 65 
        if price > last['EMA_20']: score += 10
        if price > last['EMA_200']: score += 15
        if last['RSI'] < 35: score += 15
        
        win_p = max(min(score, 98), 35)
        tp = price + (last['ATR'] * 2.3)
        sl = price - (last['ATR'] * 1.6)
        
        plt.figure(figsize=(10, 6))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc', label='Price')
        plt.title(f"AI Analysis: {symbol}")
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return {'symbol': symbol, 'price': price, 'win_p': win_p, 'tp': tp, 'sl': sl}, buf
    except: return None, None

# --- هندلرهای تلگرام ---
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
        await update.message.reply_text(f"سلام {name}! خوش آمدی.\nبرای استفاده از تحلیل‌های هوشمند، لایسنس تهیه کن.")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    
    # --- بخش مدیریت ادمین ---
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
            
            response = "👤 **لیست کاربران فعال:**\n\n"
            for u_id, u_name in users:
                response += f"🔹 نام: {u_name} | آیدی: `{u_id}`\n"
                response += f"برای حذف: /del_{u_id}\n\n"
            await update.message.reply_text(response, parse_mode='Markdown')
            return

    # حذف کاربر با دستور
    if text.startswith("/del_") and int(uid) == ADMIN_ID:
        target_id = text.replace("/del_", "")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM users WHERE user_id=?", (target_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ کاربر {target_id} با موفقیت حذف شد.")
        return

    # --- بخش پیشنهاد طلایی ---
    if text == '🔥 پیشنهاد طلایی':
        wait_msg = await update.message.reply_text("🔎 در حال اسکن بازار...")
        # فقط ۵ ارز اول برای جلوگیری از هنگ کردن
        scan_list = list(COIN_MAP.keys())[:5]
        best_sig = None
        max_win = 0
        
        for coin in scan_list:
            res, _ = get_signal(coin)
            if res and res['win_p'] > max_win:
                max_win = res['win_p']
                best_sig = res
        
        if best_sig:
            result_text = (
                f"🌟 **بهترین پیشنهاد فعلی:**\n\n"
                f"🪙 ارز: {best_sig['symbol']}\n"
                f"📈 شانس برد: `{best_sig['win_p']}%` \n"
                f"💰 قیمت ورود: `{best_sig['price']:,.4f}`\n\n"
                f"تحلیل کامل را در بخش 'لیست ارزها' ببینید."
            )
            await wait_msg.edit_text(result_text, parse_mode='Markdown')
        else:
            await wait_msg.edit_text("❌ فعلاً سیگنال قوی پیدا نشد. دوباره تلاش کنید.")
        return

    # --- سایر بخش‌ها ---
    if text == '⏳ اعتبار باقی‌مانده':
        conn = sqlite3.connect(DB_PATH)
        user = conn.execute("SELECT expiry FROM users WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        if user:
            rem = user[0] - time.time()
            days = int(rem // 86400)
            hours = int((rem % 86400) // 3600)
            await update.message.reply_text(f"⏳ اشتراک شما: {days} روز و {hours} ساعت باقی است.")
        return

    if text.startswith("VIP-"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        res = c.execute("SELECT days FROM licenses WHERE key=?", (text,)).fetchone()
        if res:
            expiry = time.time() + (res[0] * 86400)
            c.execute("DELETE FROM licenses WHERE key=?", (text,))
            c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (uid, update.effective_user.first_name, expiry))
            conn.commit()
            await update.message.reply_text("✅ فعال شد! /start را بزنید.")
        else:
            await update.message.reply_text("❌ لایسنس معتبر نیست.")
        conn.close()
        return

    if text == '💰 لیست ارزها':
        btns = [[InlineKeyboardButton(k, callback_data=k) for k in list(COIN_MAP.keys())[i:i+2]] for i in range(0, len(COIN_MAP), 2)]
        await update.message.reply_text("انتخاب ارز:", reply_markup=InlineKeyboardMarkup(btns))

    if text == '🎓 راهنمای جامع':
        await update.message.reply_text("اینجا راهنمای ترید است...")

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("در حال دریافت تحلیل...")
    res, chart = get_signal(query.data)
    if res:
        cap = f"📊 **تحلیل {res['symbol']}**\n\n🎯 شانس برد: `{res['win_p']}%` \n💰 قیمت ورود: `{res['price']:,.4f}`\n✅ حد سود: `{res['tp']:,.4f}`\n❌ حد ضرر: `{res['sl']:,.4f}`"
        await context.bot.send_photo(update.effective_chat.id, chart, caption=cap, parse_mode='Markdown')

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.run_polling()
