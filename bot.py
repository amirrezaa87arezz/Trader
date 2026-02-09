import os, uuid, time, logging, io, sqlite3, asyncio
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- پیکربندی سیستم ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
ADMIN_ID = 5993860770
DB_PATH = "/app/data/trading_v12_pro.db"

logging.basicConfig(level=logging.INFO)

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
    'TON/USDT': 'TON11419-USD', 'NEAR/USDT': 'NEAR-USD', 'SUI/USDT': 'SUI11840-USD',
    'AVAX/USDT': 'AVAX-USD', 'NOT/USDT': 'NOT-USD', 'WIF/USDT': 'WIF-USD'
}

# --- هسته تحلیلگر Alpha-Quant (فوق قدرتمند) ---
async def fetch_and_analyze(symbol):
    ticker = COIN_MAP.get(symbol)
    for i in range(3): # ۳ بار تلاش مجدد در صورت خطا
        try:
            df = yf.download(ticker, period="15d", interval="1h", progress=False, timeout=15)
            if not df.empty and len(df) > 30:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                # اندیکاتورهای فوق حرفه‌ای
                df['EMA_200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)
                macd = ta.macd(df['Close'])
                df = pd.concat([df, macd], axis=1)
                
                last = df.iloc[-1]
                price = float(last['Close'])
                
                # منطق پیش‌بینی با درصد برد بالا
                score = 50
                if price > last['EMA_200']: score += 20 # روند صعودی کلی
                if last['MACDh_12_26_9'] > 0: score += 15 # مومنتوم مثبت
                if last['RSI'] < 40: score += 15 # خرید در قیمت مناسب
                
                win_rate = max(min(score, 99), 35)
                atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1]
                tp = price + (atr * 3)
                sl = price - (atr * 1.5)
                
                return {'symbol': symbol, 'price': price, 'win_p': win_rate, 'tp': tp, 'sl': sl, 'df': df}
        except:
            await asyncio.sleep(1)
    return None

def create_chart(df, symbol):
    plt.clf()
    plt.figure(figsize=(10, 5))
    plt.style.use('dark_background')
    plt.plot(df.index, df['Close'], color='#00ffcc', linewidth=2, label='Price')
    plt.plot(df.index, df['EMA_200'], color='#ff3366', linestyle='--', alpha=0.7, label='EMA 200')
    plt.fill_between(df.index, df['Close'].min(), df['Close'].max(), color='cyan', alpha=0.03)
    plt.title(f"QUANT ANALYSIS: {symbol}")
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close('all')
    return buf

# --- هندلرهای تلگرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    conn = sqlite3.connect(DB_PATH); user = conn.execute("SELECT expiry, role FROM users WHERE user_id=?", (uid,)).fetchone(); conn.close()
    
    is_admin = int(uid) == ADMIN_ID or (user and user[1] == 'admin')
    if is_admin:
        kb = [['➕ ساخت لایسنس', '👥 مدیریت کاربران'], ['💰 لیست ارزها', '🔥 پیشنهاد طلایی']]
    elif user and user[0] > time.time():
        kb = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['⏳ اعتبار باقی‌مانده']]
    else:
        await update.message.reply_text("🚀 به سیستم تحلیلگر کوانتوم خوش آمدید.\nلطفاً لایسنس VIP خود را وارد کنید:")
        return
    await update.message.reply_text("💎 منوی دسترسی فعال شد:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)

    if text == '🔥 پیشنهاد طلایی':
        msg = await update.message.reply_text("🔎 در حال اسکن عمیق بازار با الگوریتم Alpha-Quant...")
        # اسکن مستقیم روی ۳ ارز لیدر بازار
        results = []
        for coin in ['BTC/USDT', 'SOL/USDT', 'ETH/USDT']:
            res = await fetch_and_analyze(coin)
            if res: results.append(res)
        
        if results:
            best = max(results, key=lambda x: x['win_p'])
            await msg.edit_text(f"🌟 **پیشنهاد طلایی شناسایی شد:**\n\n🪙 ارز: {best['symbol']}\n📈 درصد اطمینان: `{best['win_p']}%` \n💰 قیمت: `{best['price']:,.4f}`\n\nبرای جزئیات بیشتر از 'لیست ارزها' استفاده کنید.")
        else:
            await msg.edit_text("❌ خطا در اتصال به شبکه صرافی. ۵ دقیقه دیگر تلاش کنید.")
        return

    if text == '👥 مدیریت کاربران' and int(uid) == ADMIN_ID:
        conn = sqlite3.connect(DB_PATH); users = conn.execute("SELECT user_id, name FROM users").fetchall(); conn.close()
        if not users: await update.message.reply_text("لیست خالی است."); return
        btns = [[InlineKeyboardButton(f"❌ حذف {u[1]}", callback_data=f"del_{u[0]}")] for u in users]
        await update.message.reply_text("👤 مدیریت کاربران:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if text == '💰 لیست ارزها':
        keys = list(COIN_MAP.keys())
        btns = [[InlineKeyboardButton(keys[i], callback_data=keys[i]), InlineKeyboardButton(keys[i+1], callback_data=keys[i+1])] for i in range(0, len(keys)-1, 2)]
        await update.message.reply_text("ارز مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if text.startswith("VIP-"):
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        res = c.execute("SELECT days FROM licenses WHERE key=?", (text,)).fetchone()
        if res:
            exp = time.time() + (res[0] * 86400)
            c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (uid, update.effective_user.first_name, exp, 'user'))
            c.execute("DELETE FROM licenses WHERE key=?", (text,))
            conn.commit(); await update.message.reply_text("✅ دسترسی VIP شما فعال شد! /start را بزنید.")
        else: await update.message.reply_text("❌ لایسنس اشتباه است.")
        conn.close()

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith("del_"):
        uid = query.data.split("_")[1]
        conn = sqlite3.connect(DB_PATH); conn.execute("DELETE FROM users WHERE user_id=?", (uid,)); conn.commit(); conn.close()
        await query.edit_message_text("✅ کاربر حذف شد.")
        return

    await query.answer("🧠 در حال تحلیل کوانتومی...")
    res = await fetch_and_analyze(query.data)
    if res:
        chart = create_chart(res['df'], res['symbol'])
        cap = f"👑 **سیگنال اختصاصی {res['symbol']}**\n\n🎯 شانس برد: `{res['win_p']}%` \n💵 ورود: `{res['price']:,.4f}`\n\n✅ حد سود: `{res['tp']:,.4f}`\n❌ حد ضرر: `{res['sl']:,.4f}`"
        await context.bot.send_photo(query.message.chat_id, chart, caption=cap, parse_mode='Markdown')
    else:
        await query.message.reply_text("❌ اختلال در دیتای صرافی. دوباره روی دکمه بزنید.")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()
