import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- تنظیمات ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
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
        # دانلود دیتا با تنظیم متغیر جدید برای رفع باگ ستون‌ها
        data = yf.download(ticker, period="10d", interval="1h", progress=False)
        
        if data is None or data.empty:
            return None
        
        # اصلاح ساختار ستون‌ها برای نسخه جدید yfinance
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # محاسبه اندیکاتورها با اطمینان از وجود دیتا
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI']) if not pd.isna(last['RSI']) else 50
        atr = float(last['ATR']) if not pd.isna(last['ATR']) else (price * 0.02)
        
        score = 0
        if price > float(last['EMA_20']): score += 1
        if rsi < 35: score += 2
        if rsi > 65: score -= 2

        return {
            'score': score, 'price': price, 'rsi': rsi,
            'tp': price + (atr * 2), 'sl': price - (atr * 1.5)
        }
    except Exception as e:
        print(f"Error in analysis: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_ID
    USER_ID = update.effective_chat.id
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    await update.message.reply_text(
        "✅ **ربات با موفقیت متصل شد**\n\nتحلیل هوشمند بازار آماده است. یک ارز را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # نمایش پیام در حال پردازش برای کاربر
    await query.edit_message_text("🔄 در حال دریافت دیتای زنده...")
    
    res = analyze_logic(query.data)
    if not res:
        await query.edit_message_text("⚠️ خطا در ارتباط با بازار. دوباره تلاش کنید.")
        return

    status = "🟢 خرید" if res['score'] >= 1 else "🔴 فروش" if res['score'] <= -1 else "🟡 خنثی"
    result_text = (f"💎 **تحلیل {query.data}**\n\n💰 قیمت: {res['price']:,.2f}\n🎯 وضعیت: {status}\n"
                   f"🚀 حد سود: {res['tp']:,.2f}\n🛑 حد ضرر: {res['sl']:,.2f}\n📊 RSI: {res['rsi']:.1f}")
    
    keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data=query.data)], [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    await query.edit_message_text(text=result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    await query.edit_message_text("ارز مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    # استفاده از سیستم ساده بدون JobQueue برای رفع خطای ری‌لیوی
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(back, pattern="back"))
    application.add_handler(CallbackQueryHandler(handle_selection))
    
    print("Bot is starting...")
    application.run_polling(drop_pending_updates=True)
    
