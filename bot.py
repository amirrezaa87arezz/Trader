import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- تنظیمات توکن ---
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
        # دانلود دیتا با مدیریت خطای شبکه
        data = yf.download(ticker, period="10d", interval="1h", progress=False, multi_level_index=False)
        
        if data is None or data.empty or len(data) < 50:
            return None
        
        df = data.copy()
        # پاکسازی نام ستون‌ها برای اطمینان
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        
        # محاسبه اندیکاتورها
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI']) if not pd.isna(last['RSI']) else 50
        ema20 = float(last['EMA_20']) if not pd.isna(last['EMA_20']) else price
        ema50 = float(last['EMA_50']) if not pd.isna(last['EMA_50']) else price
        atr = float(last['ATR']) if not pd.isna(last['ATR']) else (price * 0.02)
        
        score = 0
        if price > ema20 and ema20 > ema50: score += 2
        if rsi < 35: score += 2
        if price < ema20: score -= 2
        if rsi > 65: score -= 2

        return {
            'score': score, 'price': price, 'rsi': rsi,
            'tp': price + (atr * 2), 'sl': price - (atr * 1.5)
        }
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

async def market_scanner(context: ContextTypes.DEFAULT_TYPE):
    global USER_ID
    if USER_ID is None: return
    for symbol in COIN_MAP.keys():
        res = analyze_logic(symbol)
        if res and res['score'] >= 3:
            msg = (f"🔔 **فرصت خرید شناسایی شد**\n\n💎 ارز: {symbol}\n💵 قیمت: {res['price']:,.2f}\n"
                   f"🎯 هدف: {res['tp']:,.2f}\n🛑 حد ضرر: {res['sl']:,.2f}")
            try:
                await context.bot.send_message(chat_id=USER_ID, text=msg, parse_mode='Markdown')
            except: pass
        await asyncio.sleep(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_ID
    USER_ID = update.effective_chat.id
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    await update.message.reply_text(
        "🚀 **ربات تریدر هوشمند (نسخه اصلاح شده)**\n\nاسکنر خودکار فعال شد. برای تحلیل دستی یکی از ارزها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data
    
    res = analyze_logic(symbol)
    if not res:
        await query.edit_message_text("⚠️ سرور صرافی شلوغ است. لطفاً دوباره دکمه را بزنید.")
        return

    status = "🟢 سیگنال خرید" if res['score'] >= 2 else "🔴 هشدار فروش" if res['score'] <= -2 else "🟡 خنثی"
    result_text = (f"✨ **تحلیل {symbol}**\n\n💰 قیمت: {res['price']:,.2f}\n🎯 وضعیت: {status}\n"
                   f"🚀 حد سود: {res['tp']:,.2f}\n🛑 حد ضرر: {res['sl']:,.2f}\n📊 RSI: {res['rsi']:.1f}")
    
    keyboard = [[InlineKeyboardButton("🔄 آپدیت", callback_data=symbol)], [InlineKeyboardButton("🔙 لیست", callback_data="back")]]
    await query.edit_message_text(text=result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    await query.edit_message_text("ارز مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    if app.job_queue:
        app.job_queue.run_repeating(market_scanner, interval=1800, first=10)
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    app.add_handler(CallbackQueryHandler(handle_selection))
    app.run_polling()
    
