import os
import ccxt
import pandas as pd
import pandas_ta as ta
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- تنظیمات توکن ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"

# تلاش برای اتصال به صرافی‌های مختلف در صورت خطا
def get_exchange():
    # صرافی کوکوین معمولاً با آی‌پی سرورها مشکل کمتری دارد
    return ccxt.kucoin({'enableRateLimit': True})

COINS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT']

def professional_prediction(symbol):
    try:
        ex = get_exchange()
        # دریافت داده‌ها
        bars = ex.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        if not bars:
            return "⚠️ صرافی پاسخی نداد. لطفاً لحظاتی دیگر تلاش کنید."

        df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        # محاسبه اندیکاتورهای فوق پیشرفته
        df['RSI'] = ta.rsi(df['close'], length=14)
        bbands = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        df['EMA_200'] = ta.ema(df['close'], length=200)
        
        last = df.iloc[-1]
        price = last['close']
        rsi = last['RSI']
        lower_bb = last['BBL_20_2.0']
        upper_bb = last['BBU_20_2.0']
        ema_200 = last['EMA_200']

        # سیستم امتیازدهی دقیق برای حداقل خطا
        score = 0
        if rsi < 32: score += 2
        if price <= lower_bb: score += 1.5
        if price > ema_200: score += 1
        
        if rsi > 68: score -= 2
        if price >= upper_bb: score -= 1.5
        if price < ema_200: score -= 1

        if score >= 2.5:
            res = "🚀 **سیگنال خرید قطعی**\n✅ بازار در وضعیت کف‌سازی است.\n🎯 پیش‌بینی: صعودی"
        elif score <= -2.5:
            res = "⚠️ **سیگنال فروش/خطر**\n❌ احتمال ریزش قیمت بسیار بالاست.\n🛑 پیش‌بینی: نزولی"
        else:
            res = "⚖️ **وضعیت نوسانی**\nنقطه ورود امن مشاهده نشد. صبر کنید."

        return (f"💎 **تحلیل تخصصی {symbol}**\n"
                f"💰 قیمت: {price}\n"
                f"📊 قدرت بازار (RSI): {round(rsi, 1)}\n"
                f"----------------------------------\n"
                f"{res}")

    except Exception as e:
        print(f"Error: {e}")
        return "⚠️ اختلال در شبکه صرافی. لطفاً دوباره کلیک کنید یا ارز دیگری را امتحان کنید."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COINS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🧠 **ربات پیش‌بین هوشمند (نسخه ضدخطا)**\n\nارز مورد نظر را برای تحلیل انتخاب کنید:", 
        reply_markup=reply_markup, parse_mode='Markdown'
    )

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    symbol = query.data
    await query.answer()
    
    await query.edit_message_text(text=f"🔄 در حال استخراج داده‌های زنده {symbol}...")
    result = professional_prediction(symbol)
    
    keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data=symbol)], [InlineKeyboardButton("🔙 لیست", callback_data="back")]]
    await query.edit_message_text(text=result, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COINS]
    await query.edit_message_text("ارز مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    app.add_handler(CallbackQueryHandler(handle_selection))
    print("ربات فعال شد.")
    app.run_polling()
    
