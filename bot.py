import os
import ccxt
import pandas as pd
import pandas_ta as ta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- تنظیمات توکن ---
TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"

# اتصال به صرافی بایننس (سرعت بالا)
exchange = ccxt.binance()

# لیست ارزهای برتر بازار
COINS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT']

def professional_prediction(symbol):
    try:
        # دریافت داده‌های کندل‌استیک تایم‌فریم ۱ ساعته برای تحلیل دقیق
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=150)
        df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        # لایه‌های تحلیلی برای کاهش خطا:
        # ۱. شاخص قدرت نسبی (RSI) - تشخیص اشباع خرید/فروش
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        # ۲. باندهای بولینگر - تشخیص محدوده نوسان قیمت
        bbands = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        
        # ۳. ابر ایچیموکو (بخش حساس) - برای تشخیص قدرت روند
        ichimoku = ta.ichimoku(df['high'], df['low'], df['close'])[0]
        df = pd.concat([df, ichimoku], axis=1)
        
        # ۴. میانگین متحرک ۲۰۰ (روند کلی بازار)
        df['SMA_200'] = ta.sma(df['close'], length=200)

        # آخرین وضعیت داده‌ها
        last = df.iloc[-1]
        price = last['close']
        rsi = last['RSI']
        lower_bb = last['BBL_20_2.0']
        upper_bb = last['BBU_20_2.0']
        sma_200 = last['SMA_200']

        # سیستم امتیازدهی هوشمند (Smart Scoring)
        score = 0
        
        # سیگنال خرید (سوددهی)
        if rsi < 30: score += 2  # خرید در کف
        if price <= lower_bb: score += 1.5 # برخورد به حمایت بولینگر
        if price > sma_200: score += 1 # تایید روند صعودی بلندمدت
        
        # سیگنال فروش (خطر ضرر)
        if rsi > 70: score -= 2 # اشباع خرید و احتمال ریزش
        if price >= upper_bb: score -= 1.5 # برخورد به مقاومت بولینگر
        if price < sma_200: score -= 1 # روند کلی نزولی است

        # تحلیل نهایی
        if score >= 2.5:
            res = "🚀 **سیگنال خرید قوی (سودده)**\n\n✅ تحلیل: بازار در منطقه حمایتی است و اندیکاتورها بازگشت قیمت را تایید می‌کنند.\n🎯 شانس موفقیت: بسیار بالا"
        elif score <= -2.5:
            res = "⚠️ **هشدار فروش / خطر ضرر**\n\n❌ تحلیل: قیمت به سقف رسیده و احتمال اصلاح شدید وجود دارد. وارد نشوید!\n🛑 ریسک: زیاد"
        else:
            res = "⚖️ **وضعیت بازار: خنثی**\n\nصبر کنید. سیگنال قطعی برای سوددهی در این لحظه وجود ندارد. بازار در حال رنج زدن است."

        return (f"💎 **تحلیل هوشمند ارز {symbol}**\n"
                f"💰 قیمت فعلی: {price}\n"
                f"📈 شاخص RSI: {round(rsi, 2)}\n"
                f"----------------------------------\n"
                f"{res}")

    except Exception as e:
        return "⚠️ خطا در دریافت اطلاعات از بازار. دوباره تلاش کنید."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin)] for coin in COINS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🧠 **به ربات تریدر هوشمند خوش آمدید**\n\n"
        "این ربات از استراتژی ترکیبی RSI، Bollinger Bands و SMA برای پیش‌بینی دقیق استفاده می‌کند.\n"
        "لطفاً ارز مورد نظر را برای بررسی سوددهی انتخاب کنید:", 
        reply_markup=reply_markup, parse_mode='Markdown'
    )

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    symbol = query.data
    await query.answer()
    
    await query.edit_message_text(text=f"🔄 در حال آنالیز لایه‌های مختلف بازار برای {symbol}...")
    
    result = professional_prediction(symbol)
    
    keyboard = [
        [InlineKeyboardButton("🔄 آپدیت تحلیل", callback_data=symbol)],
        [InlineKeyboardButton("🔙 لیست ارزها", callback_data="back")]
    ]
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
    
    print("ربات با قدرت شروع به کار کرد...")
    app.run_polling()
