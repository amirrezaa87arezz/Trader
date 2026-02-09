import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- تنظیمات توکن ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"

# لیست ارزها با فرمت استاندارد جهانی
COIN_MAP = {
    'BTC/USDT': 'BTC-USD',
    'ETH/USDT': 'ETH-USD',
    'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD',
    'ADA/USDT': 'ADA-USD',
    'DOGE/USDT': 'DOGE-USD'
}

def get_smart_prediction(symbol):
    try:
        ticker_symbol = COIN_MAP.get(symbol)
        # دریافت داده‌های اخیر از منبع معتبر Yahoo Finance (بدون تحریم و خطا)
        data = yf.download(ticker_symbol, period="7d", interval="1h", progress=False)
        
        if data.empty:
            return "❌ خطا: دیتای بازار در دسترس نیست."

        df = data.copy()
        # اندیکاتورهای فوق حرفه‌ای
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        
        current_price = float(df['Close'].iloc[-1])
        rsi = float(df['RSI'].iloc[-1])
        ema20 = float(df['EMA_20'].iloc[-1])
        ema50 = float(df['EMA_50'].iloc[-1])

        # سیستم امتیازدهی هوشمند برای پیش‌بینی سود یا ضرر
        score = 0
        if current_price > ema20 and ema20 > ema50: score += 2  # روند صعودی قوی
        if rsi < 35: score += 2  # قیمت در کف (فرصت خرید)
        if current_price < ema20: score -= 2  # شروع ریزش
        if rsi > 65: score -= 2  # قیمت در سقف (خطر ضرر)

        if score >= 2:
            status = "🟢 **پرسود (پیش‌بینی صعودی)**"
            note = "تحلیل هوشمند: سیگنال خرید صادر شده است. احتمال سوددهی بسیار بالاست."
        elif score <= -2:
            status = "🔴 **ضررده (پیش‌بینی نزولی)**"
            note = "تحلیل هوشمند: بازار در وضعیت اشباع است. احتمال ضرر در صورت ورود بسیار زیاد است."
        else:
            status = "🟡 **خنثی (بدون جهت)**"
            note = "سیگنال قطعی وجود ندارد. برای معامله امن، منتظر فرصت بعدی بمانید."

        return (f"✨ **تحلیل فوق حرفه‌ای {symbol}**\n\n"
                f"💵 قیمت لحظه‌ای: {current_price:,.2f} دلار\n"
                f"📊 شاخص قدرت (RSI): {rsi:.1f}\n"
                f"━━━━━━━━━━━━━━\n"
                f"🎯 نتیجه پیش‌بینی: {status}\n\n"
                f"💡 راهنما: {note}")

    except Exception as e:
        return f"⚠️ خطای سیستمی: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🚀 **به ربات تریدر هوشمند خوش آمدید**\n\n"
        "این ربات با تحلیل چندین لایه تکنیکال، ارزهای پرسود را پیش‌بینی می‌کند.\n"
        "ارز مورد نظر را از لیست انتخاب کنید:", 
        reply_markup=reply_markup, parse_mode='Markdown'
    )

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    symbol = query.data
    await query.answer()
    await query.edit_message_text(text=f"🔬 در حال پردازش لایه‌های قیمتی {symbol}...")
    result = get_smart_prediction(symbol)
    keyboard = [[InlineKeyboardButton("🔄 آپدیت تحلیل", callback_data=symbol)], [InlineKeyboardButton("🔙 لیست ارزها", callback_data="back")]]
    await query.edit_message_text(text=result, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COIN_MAP.keys()]
    await update.callback_query.edit_message_text("ارز مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    app.add_handler(CallbackQueryHandler(handle_selection))
    print("Bot is Running...")
    app.run_polling()
    
