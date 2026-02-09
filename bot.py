import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# تنظیمات لاگ برای دیدن جزئیات در Railway
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"

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
        data = yf.download(ticker, period="10d", interval="1h", progress=False)
        
        if data is None or data.empty:
            return None
        
        df = data.copy()
        # حذف لایه‌های اضافی ستون‌ها که در نسخه‌های جدید yfinance ایجاد می‌شود
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI']) if not pd.isna(last['RSI']) else 50
        atr = float(last['ATR']) if not pd.isna(last['ATR']) else (price * 0.02)
        
        score = 0
        if rsi < 35: score += 1
        if rsi > 65: score -= 1

        return {
            'score': score, 'price': price, 'rsi': rsi,
            'tp': price + (atr * 2), 'sl': price - (atr * 1.5)
        }
    except Exception as e:
        logging.error(f"Error in analysis for {symbol}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    await update.message.reply_text(
        "🚀 **ربات با پایتون 3.13 هماهنگ شد**\n\nیک ارز را برای تحلیل انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    symbol = query.data
    if symbol == "back":
        keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
        await query.edit_message_text("ارز مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await query.edit_message_text(f"🔄 در حال تحلیل {symbol}...")
    
    res = analyze_logic(symbol)
    if not res:
        await query.edit_message_text("⚠️ خطا در دریافت دیتا. دوباره تلاش کنید.")
        return

    status = "🟢 خرید" if res['score'] >= 1 else "🔴 فروش" if res['score'] <= -1 else "🟡 خنثی"
    result_text = (f"💎 **تحلیل {symbol}**\n\n💰 قیمت: {res['price']:,.2f}\n🎯 وضعیت: {status}\n"
                   f"🚀 حد سود: {res['tp']:,.2f}\n🛑 حد ضرر: {res['sl']:,.2f}\n📊 RSI: {res['rsi']:.1f}")
    
    keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data=symbol)], [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    await query.edit_message_text(text=result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

if __name__ == '__main__':
    # ساخت اپلیکیشن با تنظیمات ساده برای جلوگیری از ارور Updater
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_selection))
    
    print("Bot is starting on Python 3.13...")
    application.run_polling(drop_pending_updates=True)
    
