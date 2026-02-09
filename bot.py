import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- تنظیمات توکن و چت ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
# آیدی عددی شما برای ارسال هشدار (بعد از زدن /start ربات آن را پیدا می‌کند)
USER_ID = None 

COIN_MAP = {
    'BTC/USDT': 'BTC-USD',
    'ETH/USDT': 'ETH-USD',
    'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD',
    'ADA/USDT': 'ADA-USD',
    'DOGE/USDT': 'DOGE-USD'
}

def analyze_logic(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        data = yf.download(ticker, period="5d", interval="1h", progress=False)
        if data.empty: return None
        
        df = data.copy()
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price, rsi, ema20, ema50, atr = float(last['Close']), float(last['RSI']), float(last['EMA_20']), float(last['EMA_50']), float(last['ATR'])
        
        score = 0
        if price > ema20 and ema20 > ema50: score += 2
        if rsi < 35: score += 2
        if price < ema20: score -= 2
        if rsi > 65: score -= 2

        return {
            'score': score,
            'price': price,
            'rsi': rsi,
            'tp': price + (atr * 2),
            'sl': price - (atr * 1.5)
        }
    except: return None

# تابع اسکنر خودکار بازار
async def market_scanner(context: ContextTypes.DEFAULT_TYPE):
    global USER_ID
    if USER_ID is None: return

    for symbol in COIN_MAP.keys():
        res = analyze_logic(symbol)
        if res and res['score'] >= 3: # فقط سیگنال‌های خیلی قوی
            msg = (f"🔔 **هشدار فرصت خرید (طلایی)**\n\n"
                   f"💎 ارز: {symbol}\n"
                   f"💵 قیمت: {res['price']:,.2f}\n"
                   f"🎯 هدف سود: {res['tp']:,.2f}\n"
                   f"🛑 حد ضرر: {res['sl']:,.2f}\n"
                   f"📈 شاخص RSI: {res['rsi']:.1f}\n\n"
                   f"⚠️ همین حالا بررسی کنید!")
            await context.bot.send_message(chat_id=USER_ID, text=msg, parse_mode='Markdown')
        await asyncio.sleep(2) # وقفه کوتاه برای جلوگیری از مسدودی

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_ID
    USER_ID = update.effective_chat.id
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    await update.message.reply_text(
        "⚡️ **ربات شکارچی سود فعال شد!**\n\n"
        "۱. از لیست زیر برای تحلیل دستی استفاده کنید.\n"
        "۲. سیستم اسکنر خودکار فعال شد؛ هر وقت موقعیت عالی پیدا کنم بهتون خبر میدم.",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    res = analyze_logic(query.data)
    if not res:
        await query.edit_message_text("⚠️ خطا در دریافت اطلاعات.")
        return

    status = "🟢 خرید" if res['score'] >= 2 else "🔴 فروش/خطر" if res['score'] <= -2 else "🟡 خنثی"
    result_text = (f"✨ **تحلیل {query.data}**\n\n"
                   f"💰 قیمت: {res['price']:,.2f}\n"
                   f"🎯 نتیجه: {status}\n"
                   f"🚀 TP: {res['tp']:,.2f}\n"
                   f"🛑 SL: {res['sl']:,.2f}\n")
    
    keyboard = [[InlineKeyboardButton("🔄 آپدیت", callback_data=query.data)], [InlineKeyboardButton("🔙 لیست", callback_data="back")]]
    await query.edit_message_text(text=result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    await query.edit_message_text("ارز مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # تنظیم اجرای اسکنر هر ۳۰ دقیقه یکبار
    job_queue = app.job_queue
    job_queue.run_repeating(market_scanner, interval=1800, first=10)
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    app.add_handler(CallbackQueryHandler(handle_selection))
    
    print("Super Bot is Scanning Market...")
    app.run_polling()
    
