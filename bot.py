import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import io
import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = "8154056569:AAFdWvFe7YzrAmAIV4BgsBnq20VSCmA_TZ0"
USER_CAPITAL = 1000 # سرمایه پیش‌فرض

COIN_MAP = {
    'BTC/USDT': 'BTC-USD', 'ETH/USDT': 'ETH-USD', 'SOL/USDT': 'SOL-USD',
    'BNB/USDT': 'BNB-USD', 'DOGE/USDT': 'DOGE-USD', 'NEAR/USDT': 'NEAR-USD',
    'PEPE/USDT': 'PEPE-USD', 'LINK/USDT': 'LINK-USD', 'AVAX/USDT': 'AVAX-USD'
}

def generate_chart(symbol, data):
    plt.figure(figsize=(10, 5))
    plt.style.use('dark_background') # تم تاریک برای ظاهر حرفه‌ای‌تر
    plt.plot(data.index, data['Close'], label='قیمت', color='#00ffcc', linewidth=2)
    plt.fill_between(data.index, data['Close'], alpha=0.1, color='#00ffcc')
    plt.title(f"{symbol} - Trend Analysis")
    plt.grid(True, linestyle='--', alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def analyze_logic(symbol):
    try:
        ticker = COIN_MAP.get(symbol)
        data = yf.download(ticker, period="5d", interval="1h", progress=False)
        if data is None or data.empty: return None, None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI']) if not pd.isna(last['RSI']) else 50
        atr = float(last['ATR']) if not pd.isna(last['ATR']) else (price * 0.02)
        
        # فرمول شانس موفقیت
        win_p = 50 + (30 - rsi if rsi < 35 else rsi - 70 if rsi > 65 else 0)
        win_p = max(min(win_p, 95), 5)
        
        tp = price + (atr * 2.5)
        sl = price - (atr * 1.5)
        
        # مدیریت سرمایه و ماشین حساب سود
        risk_amount = USER_CAPITAL * 0.02 # ضرر ثابت ۲ درصدی
        stop_loss_pct = abs(price - sl) / price
        pos_size = risk_amount / stop_loss_pct
        
        take_profit_pct = abs(tp - price) / price
        expected_profit = pos_size * take_profit_pct
        
        chart_buf = generate_chart(symbol, df)
        
        res = {
            'symbol': symbol, 'price': price, 'rsi': int(rsi),
            'tp': tp, 'sl': sl, 'win_p': int(win_p),
            'pos_size': pos_size, 'profit_usd': expected_profit, 'risk_usd': risk_amount
        }
        return res, chart_buf
    except:
        return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    main_menu = [['💰 لیست ارزها', '🔥 پیشنهاد طلایی'], ['⚙️ تنظیم سرمایه', '📊 راهنما']]
    reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    await update.message.reply_text(
        "💎 **دستیار ترید همه‌کاره آماده است!**\n\nیک گزینه را انتخاب کنید:",
        reply_markup=reply_markup, parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_CAPITAL
    text = update.message.text
    
    if text == '💰 لیست ارزها':
        keys = list(COIN_MAP.keys())
        keyboard = [keys[i:i+2] for i in range(0, len(keys), 2)]
        inline_markup = InlineKeyboardMarkup([[InlineKeyboardButton(c, callback_data=c) for c in row] for row in keyboard])
        await update.message.reply_text("ارز مورد نظر را انتخاب کنید:", reply_markup=inline_markup)
    
    elif text == '⚙️ تنظیم سرمایه':
        await update.message.reply_text("لطفاً کل موجودی کیف پول خود را به عدد (دلار) بفرستید:")
        
    elif text.isdigit():
        USER_CAPITAL = int(text)
        await update.message.reply_text(f"✅ سرمایه شما روی `{USER_CAPITAL}$` تنظیم شد.")

async def handle_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data
    
    msg = await query.message.reply_text(f"🔄 در حال انجام محاسبات مالی برای {symbol}...")
    res, chart_buf = analyze_logic(symbol)
    
    if res:
        result_text = (
            f"📊 **تحلیل و ماشین‌حساب {res['symbol']}**\n"
            f"━━━━━━━━━━━━━━\n"
            f"🚀 شانس موفقیت: `{res['win_p']}%` | RSI: `{res['rsi']}`\n"
            f"💵 قیمت کنونی: `{res['price']:,.4f}`\n\n"
            f"📏 **پلن مدیریت معامله:**\n"
            f"💰 حجم ورود: `{res['pos_size']:,.1f} دلار`\n"
            f"🎯 هدف: `{res['tp']:,.4f}`\n"
            f"🛑 حد ضرر: `{res['sl']:,.4f}`\n\n"
            f"💵 **تخمین سود/ضرر خالص:**\n"
            f"✅ سود در صورت موفقیت: `+{res['profit_usd']:,.2f}$`\n"
            f"❌ ضرر در صورت شکست: `-{res['risk_usd']:,.2f}$`\n"
            f"━━━━━━━━━━━━━━"
        )
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=chart_buf,
            caption=result_text,
            parse_mode='Markdown'
        )
        await msg.delete()

if __name__ == '__main__':
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_inline_buttons))
    application.run_polling(drop_pending_updates=True)
