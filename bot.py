import os, uuid, time, logging, io, sqlite3
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- تنظیمات سیستمی ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_PATH = "/app/data/trading_god_v7.db"

logging.basicConfig(level=logging.INFO)

def init_db():
    if not os.path.exists("/app/data"): os.makedirs("/app/data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (key TEXT PRIMARY KEY, days INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, expiry REAL, role TEXT)''')
    conn.commit()
    conn.close()

# --- لیست گسترده ۳۰ ارز انفجاری ---
COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'PEPE/USDT': 'PEPE-USD',
    'TON/USDT': 'TON11419-USD', 'SHIB/USDT': 'SHIB-USD', 'NEAR/USDT': 'NEAR-USD',
    'AVAX/USDT': 'AVAX-USD', 'LINK/USDT': 'LINK-USD', 'SUI/USDT': 'SUI11840-USD',
    'WIF/USDT': 'WIF-USD', 'FET/USDT': 'FET-USD', 'RNDR/USDT': 'RNDR-USD',
    'DOT/USDT': 'DOT-USD', 'MATIC/USDT': 'MATIC-USD', 'ARB/USDT': 'ARB11840-USD',
    'OP/USDT': 'OP-USD', 'ADA/USDT': 'ADA-USD', 'XRP/USDT': 'XRP-USD',
    'LTC/USDT': 'LTC-USD', 'TRX/USDT': 'TRX-USD', 'FLOKI/USDT': 'FLOKI-USD',
    'BONK/USDT': 'BONK-USD', 'NOT/USDT': 'NOT-USD', 'STX/USDT': 'STX-USD',
    'ICP/USDT': 'ICP-USD', 'JUP/USDT': 'JUP-USD', 'PYTH/USDT': 'PYTH-USD'
}

# --- هسته تحلیل‌گر فوق هوشمند (Mega AI Logic) ---
def get_beast_analysis(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        # دریافت دیتای بیشتر برای دقت بالاتر (۱۵ روز گذشته)
        df = yf.download(ticker, period="15d", interval="1h", progress=False)
        if df.empty or len(df) < 50: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # ۱. اندیکاتورهای پایه
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        
        # ۲. مکدی و بولینگر بند
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        
        # ۳. ابر ایچیموکو (بخش کلیدی)
        ichimoku = ta.ichimoku(df['High'], df['Low'], df['Close'])[0]
        df = pd.concat([df, ichimoku], axis=1)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        
        # --- سیستم امتیازدهی بی‌رحمانه ---
        score = 60
        # تاییدیه روند (Trend Confirmation)
        if price > last['EMA_20'] > last['EMA_200']: score += 15
        # تاییدیه نوسان (Momentum)
        if last['MACDh_12_26_9'] > 0: score += 10
        # تاییدیه قیمت (Price Action)
        if price < last['BBL_20_2.0']: score += 10 # کف قیمت
        if last['RSI'] < 30: score += 15 # اشباع فروش
        
        # کسر امتیاز برای امنیت
        if last['RSI'] > 75: score -= 30 # خطر سقوط

        win_p = max(min(score, 99), 32)
        
        # محاسبه TP/SL متغیر بر اساس ATR (مدیریت ریسک حرفه‌ای)
        atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1]
        tp = price + (atr * 2.8)
        sl = price - (atr * 1.5)

        # رسم نمودار سینمایی و تاریک
        plt.clf()
        plt.figure(figsize=(11, 6))
        plt.style.use('dark_background')
        plt.plot(df.index, df['Close'], color='#00ffcc', label='Price', linewidth=1.5)
        plt.plot(df.index, df['EMA_20'], color='#ff9900', label='Fast EMA', alpha=0.5)
        plt.fill_between(df.index, df['BBU_20_2.0'], df['BBL_20_2.0'], color='white', alpha=0.05)
        plt.title(f"GOD MODE ANALYSIS: {symbol}", fontsize=14, color='cyan')
        plt.grid(alpha=0.1)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        plt.close('all')
        
        return {'symbol': symbol, 'price': price, 'win_p': win_p, 'tp': tp, 'sl': sl}, buf
    except Exception as e:
        logging.error(f"Analysis Failed: {e}")
        return None, None

# --- هندلرهای تلگرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute("SELECT expiry, role FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()

    is_admin = int(uid) == ADMIN_ID or (user and user[1] == 'admin')

    if is_admin:
        kb = [['➕ ساخت لایسنس', '👥 مدیریت کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
        await update.message.reply_text("💎 مدیر ارشد، سیستم تحلیلگر V7 آماده به کار است.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif user and user[0] > time.time():
        kb = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['🎓 راهنمای جامع', '⏳ اعتبار باقی‌مانده']]
        await update.message.reply_text("🚀 دسترسی شما تایید شد. بازار در دستان توست!", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        await update.message.reply_text("🔐 لایسنس VIP خود را وارد کنید:")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    
    # ادمین - ساخت لایسنس
    if text == '➕ ساخت لایسنس' and int(uid) == ADMIN_ID:
        k = f"VIP-{uuid.uuid4().hex[:8].upper()}"
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO licenses VALUES (?, ?)", (k, 30))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ لایسنس ۳۰ روزه اتمی ساخته شد:\n`{k}`", parse_mode='Markdown')
        return

    # مدیریت کاربران (V7 - پیشرفته)
    if text == '👥 مدیریت کاربران' and int(uid) == ADMIN_ID:
        conn = sqlite3.connect(DB_PATH)
        users = conn.execute("SELECT user_id, name FROM users").fetchall()
        conn.close()
        if not users:
            await update.message.reply_text("دیتابیس کاربران خالی است.")
            return
        btns = [[InlineKeyboardButton(f"👤 {u[1]}", callback_data=f"user_{u[0]}")] for u in users]
        await update.message.reply_text("انتخاب کاربر برای حذف یا ارتقا:", reply_markup=InlineKeyboardMarkup(btns))
        return

    # پیشنهاد طلایی (اسکن عمیق)
    if text == '🔥 پیشنهاد طلایی':
        msg = await update.message.reply_text("🔦 در حال اسکن عمیق ۳۰ ارز برتر برای پیدا کردن فرصت‌های خرید...")
        best = None
        for c in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'PEPE/USDT', 'TON/USDT', 'SUI/USDT']:
            res, _ = get_beast_analysis(c)
            if res and (not best or res['win_p'] > best['win_p']): best = res
        if best:
            await msg.edit_text(f"💎 **پیشنهاد طلایی سیستم V7:**\n\nارز: {best['symbol']}\nشانس انفجار: `{best['win_p']}%` \nقیمت: `{best['price']:,.4f}`", parse_mode='Markdown')
        return

    if text == '💰 لیست ارزها':
        keys = list(COIN_MAP.keys())
        btns = [[InlineKeyboardButton(keys[i], callback_data=keys[i]), InlineKeyboardButton(keys[i+1], callback_data=keys[i+1])] if i+1 < len(keys) else [InlineKeyboardButton(keys[i], callback_data=keys[i])] for i in range(0, len(keys), 2)]
        await update.message.reply_text("انتخاب ارز از بین ۳۰ کوین پرطرفدار:", reply_markup=InlineKeyboardMarkup(btns))

    if text.startswith("VIP-"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        res = c.execute("SELECT days FROM licenses WHERE key=?", (text,)).fetchone()
        if res:
            exp = time.time() + (res[0] * 86400)
            c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (uid, update.effective_user.first_name, exp, 'user'))
            c.execute("DELETE FROM licenses WHERE key=?", (text,))
            conn.commit()
            await update.message.reply_text("🔥 اشتراک VIP فعال شد. /start را بزنید.")
        else:
            await update.message.reply_text("❌ لایسنس نامعتبر.")
        conn.close()

async def callback_worker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    # مدیریت کاربر
    if data.startswith("user_"):
        uid = data.split("_")[1]
        btns = [[InlineKeyboardButton("❌ حذف کاربر", callback_data=f"del_{uid}")], [InlineKeyboardButton("👑 ادمین کردن", callback_data=f"adm_{uid}")]]
        await query.edit_message_text(f"مدیریت آیدی: {uid}", reply_markup=InlineKeyboardMarkup(btns))
        return
    
    if data.startswith("del_"):
        uid = data.split("_")[1]
        conn = sqlite3.connect(DB_PATH); conn.execute("DELETE FROM users WHERE user_id=?", (uid,)); conn.commit(); conn.close()
        await query.edit_message_text("✅ حذف شد.")
        return

    # تحلیل ارز
    await query.answer("🧠 در حال پردازش سیگنال...")
    res, chart = get_beast_analysis(data)
    if res:
        cap = f"👑 **سیگنال ربات Trading Beast**\n\nارز: {res['symbol']}\n🎯 شانس برد: `{res['win_p']}%` \n💵 قیمت ورود: `{res['price']:,.4f}`\n\n✅ حد سود: `{res['tp']:,.4f}`\n❌ حد ضرر: `{res['sl']:,.4f}`"
        await context.bot.send_photo(query.message.chat_id, chart, caption=cap, parse_mode='Markdown')
    else:
        await query.message.reply_text("❌ خطا در اتصال به صرافی. لطفاً دوباره روی نام ارز بزنید.")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(callback_worker))
    app.run_polling()
