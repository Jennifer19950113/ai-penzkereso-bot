import os
import asyncio
import threading
import json
from urllib.request import urlopen
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", "10000"))

KRAKEN_URL = "https://api.kraken.com/0/public/OHLC?pair=XBTUSDT&interval=60"


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"AI Crypto Bot is running.")

    def log_message(self, format, *args):
        return


def start_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


def get_candles():
    with urlopen(KRAKEN_URL, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("error"):
        raise RuntimeError(str(data["error"]))

    result = data["result"]
    pair_key = next(key for key in result if key != "last")

    candles = result[pair_key]

    return [
        {
            "open": float(candle[1]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "close": float(candle[4])
        }
        for candle in candles
    ]


def calculate_ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    value = sum(values[:period]) / period

    for price in values[period:]:
        value = ((price - value) * multiplier) + value

    return value


def calculate_rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        average_gain = (
            (average_gain * (period - 1)) + gains[i]
        ) / period

        average_loss = (
            (average_loss * (period - 1)) + losses[i]
        ) / period

    if average_loss == 0:
        return 100.0

    relative_strength = average_gain / average_loss

    return 100 - (100 / (1 + relative_strength))


def calculate_atr(candles, period=14):
    if len(candles) <= period:
        return None

    true_ranges = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        previous_close = candles[i - 1]["close"]

        true_range = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )

        true_ranges.append(true_range)

    return sum(true_ranges[-period:]) / period


def calculate_signal():
    candles = get_candles()

    if len(candles) < 200:
        raise RuntimeError("Nincs elegendő piaci adat.")

    closes = [candle["close"] for candle in candles]

    price = closes[-1]

    ema20 = calculate_ema(closes, 20)
    ema200 = calculate_ema(closes, 200)
    rsi = calculate_rsi(closes, 14)
    atr = calculate_atr(candles, 14)

    if ema20 is None or ema200 is None or rsi is None or atr is None:
        raise RuntimeError("Az indikátorok kiszámítása sikertelen.")

    signal = "🟡 WAIT"
    stop_loss = None
    take_profit = None

    if ema20 > ema200 and price > ema20 and 50 <= rsi <= 70:
        signal = "🟢 BUY"
        stop_loss = price - (1.5 * atr)
        take_profit = price + (3.0 * atr)

    elif ema20 < ema200 and price < ema20 and 30 <= rsi <= 50:
        signal = "🔴 SELL"
        stop_loss = price + (1.5 * atr)
        take_profit = price - (3.0 * atr)

    return signal, price, ema20, ema200, rsi, atr, stop_loss, take_profit


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 AI Crypto Bot\n\n"
        "📊 Kraken BTC/USDT\n"
        "📈 EMA20 + EMA200\n"
        "📉 RSI + ATR\n"
        "🛑 Stop Loss / 🎯 Take Profit\n\n"
        "Valós piaci adatokat használunk."
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        candles = get_candles()
        price = candles[-1]["close"]

        await update.message.reply_text(
            f"📊 Kraken BTC/USDT\n\n"
            f"💰 Ár: {price:,.2f} USDT"
        )

    except Exception as error:
        await update.message.reply_text(
            f"❌ Árlekérési hiba:\n{error}"
        )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        (
            signal_value,
            price,
            ema20,
            ema200,
            rsi,
            atr,
            stop_loss,
            take_profit
        ) = calculate_signal()

        message = (
            "📊 BTC/USDT STRATÉGIA\n\n"
            f"{signal_value}\n\n"
            f"💰 Ár: {price:,.2f} USDT\n"
            f"📈 EMA20: {ema20:,.2f}\n"
            f"📊 EMA200: {ema200:,.2f}\n"
            f"📉 RSI: {rsi:.2f}\n"
            f"📐 ATR: {atr:,.2f}\n"
        )

        if stop_loss is not None:
            message += (
                f"\n🛑 Stop Loss: {stop_loss:,.2f} USDT\n"
                f"🎯 Take Profit: {take_profit:,.2f} USDT\n"
                "📐 R:R = 1:2\n"
            )
        else:
            message += "\n⏸️ Nincs ügylet – WAIT\n"

        message += (
            "\n🟢 Valós Kraken adat\n"
            "⚠️ Jelenleg nincs automatikus valódi megbízás."
        )

        await update.message.reply_text(message)

    except Exception as error:
        await update.message.reply_text(
            f"❌ Stratégiai hiba:\n{error}"
        )


async def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN nincs beállítva.")

    threading.Thread(
        target=start_web_server,
        daemon=True
    ).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("AI Crypto Bot fut.")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())   
