import os
import asyncio
import threading
import json
import urllib.parse
from urllib.request import urlopen, Request
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", "10000"))

KRAKEN_BASE = "https://api.kraken.com/0/public/OHLC"
PAIR = "XBTUSDT"
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = "price_1UH2Bc5dT7Ky153dsKxDE1y2"

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


def create_checkout_session(telegram_user_id):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY nincs beállítva.")

    data = {
        "mode": "subscription",
        "ui_mode": "hosted_page",
        "success_url": "https://ai-penzkereso-bot.onrender.com/success",
        "cancel_url": "https://ai-penzkereso-bot.onrender.com/cancel",
        "line_items[0][price]": STRIPE_PRICE_ID,
        "line_items[0][quantity]": "1",
        "billing_address_collection": "auto",
        "payment_method_collection": "always",
        "allow_promotion_codes": "true",
        "metadata[telegram_user_id]": str(telegram_user_id),
        "subscription_data[metadata][telegram_user_id]": str(telegram_user_id),
    }

    body = urllib.parse.urlencode(data).encode()

    request = Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    with urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode())

    if "url" not in result:
        raise RuntimeError(str(result))

    return result["url"]def get_candles(interval):
    url = f"{KRAKEN_BASE}?pair={PAIR}&interval={interval}"

    with urlopen(url, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("error"):
        raise RuntimeError(str(data["error"]))

    result = data["result"]

    pair_key = next(
        key for key in result
        if key != "last"
    )

    candles = []

    for candle in result[pair_key]:
        candles.append({
            "time": int(candle[0]),
            "open": float(candle[1]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "close": float(candle[4]),
            "volume": float(candle[6])
        })

    return candles


def calculate_ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    ema = sum(values[:period]) / period

    for price in values[period:]:
        ema = (
            (price - ema) * multiplier
        ) + ema

    return ema


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
            average_gain * (period - 1)
            + gains[i]
        ) / period

        average_loss = (
            average_loss * (period - 1)
            + losses[i]
        ) / period

    if average_loss == 0:
        return 100.0

    rs = average_gain / average_loss

    return 100 - (100 / (1 + rs))


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


def get_h4_trend():
    candles = get_candles(240)

    if len(candles) < 210:
        raise RuntimeError(
            "Nincs elegendő H4 adat."
        )

    closes = [
        candle["close"]
        for candle in candles
    ]

    ema20 = calculate_ema(closes, 20)
    ema200 = calculate_ema(closes, 200)

    current = closes[-1]

    if ema20 is None or ema200 is None:
        raise RuntimeError(
            "H4 indikátor hiba."
        )

    if current > ema20 and ema20 > ema200:
        return "BULLISH", candles, ema20, ema200

    if current < ema20 and ema20 < ema200:
        return "BEARISH", candles, ema20, ema200

    return "NEUTRAL", candles, ema20, ema200


def detect_m15_sweep(direction):
    candles = get_candles(15)

    if len(candles) < 30:
        return None, candles

    previous = candles[-2]
    current = candles[-1]

    recent = candles[-12:-2]

    recent_high = max(
        candle["high"]
        for candle in recent
    )

    recent_low = min(
        candle["low"]
        for candle in recent
    )

    if direction == "BUY":

        swept_liquidity = (
            previous["low"] < recent_low
        )

        bullish_reaction = (
            current["close"] > previous["high"]
        )

        if swept_liquidity and bullish_reaction:
            return "BUY", candles

    if direction == "SELL":

        swept_liquidity = (
            previous["high"] > recent_high
        )

        bearish_reaction = (
            current["close"] < previous["low"]
        )

        if swept_liquidity and bearish_reaction:
            return "SELL", candles

    return None, candles


def confirm_m5(direction):
    candles = get_candles(5)

    if len(candles) < 50:
        return False, candles

    closes = [
        candle["close"]
        for candle in candles
    ]

    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)
    rsi = calculate_rsi(closes, 14)

    if (
        ema20 is None
        or ema50 is None
        or rsi is None
    ):
        return False, candles

    current = candles[-1]

    if direction == "BUY":

        confirmation = (
            current["close"] > ema20
            and ema20 > ema50
            and rsi >= 50
            and rsi <= 75
        )

        return confirmation, candles

    if direction == "SELL":

        confirmation = (
            current["close"] < ema20
            and ema20 < ema50
            and rsi >= 25
            and rsi <= 50
        )

        return confirmation, candles

    return False, candles


def calculate_trade_levels(
    direction,
    m5_candles
):
    recent = m5_candles[-6:]

    entry = recent[-1]["close"]

    atr = calculate_atr(
        m5_candles,
        14
    )

    if atr is None:
        return None

    recent_high = max(
        candle["high"]
        for candle in recent[:-1]
    )

    recent_low = min(
        candle["low"]
        for candle in recent[:-1]
    )

    if direction == "BUY":

        stop_loss = recent_low - (
            atr * 0.20
        )

        risk = entry - stop_loss

        if risk <= 0:
            return None

        take_profit = entry + (
            risk * 2
        )

    else:

        stop_loss = recent_high + (
            atr * 0.20
        )

        risk = stop_loss - entry

        if risk <= 0:
            return None

        take_profit = entry - (
            risk * 2
        )

    return (
        entry,
        stop_loss,
        take_profit,
        atr
    )


def calculate_signal():
    trend, h4, h4_ema20, h4_ema200 = (
        get_h4_trend()
    )

    if trend == "NEUTRAL":
        return {
            "signal": "WAIT",
            "reason": "H4 trend semleges.",
            "trend": trend
        }

    direction = (
        "BUY"
        if trend == "BULLISH"
        else "SELL"
    )

    m15_signal, m15_candles = (
        detect_m15_sweep(direction)
    )

    if m15_signal is None:
        return {
            "signal": "WAIT",
            "reason": (
                "H4 trend megvan, "
                "de nincs M15 liquidity sweep."
            ),
            "trend": trend
        }

    confirmed, m5_candles = (
        confirm_m5(direction)
    )

    if not confirmed:
        return {
            "signal": "WAIT",
            "reason": (
                "M15 sweep megvan, "
                "de nincs M5 megerősítés."
            ),
            "trend": trend
        }

    levels = calculate_trade_levels(
        direction,
        m5_candles
    )

    if levels is None:
        return {
            "signal": "WAIT",
            "reason": (
                "Nem számítható biztonságos "
                "SL/TP."
            ),
            "trend": trend
        }

    entry, stop_loss, take_profit, atr = (
        levels
    )

    return {
        "signal": direction,
        "reason": (
            "H4 trend + M15 sweep + "
            "M5 megerősítés"
        ),
        "trend": trend,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "atr": atr,
        "h4_ema20": h4_ema20,
        "h4_ema200": h4_ema200
    }


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🤖 AI Crypto Bot\n\n"
        "📊 BTC/USDT\n\n"
        "H4 → fő trend\n"
        "M15 → liquidity sweep\n"
        "M5 → belépési megerősítés\n\n"
        "🛑 Strukturális Stop Loss\n"
        "🎯 Take Profit: R:R 1:2\n\n"
        "⚠️ Jelző mód – valódi "
        "megbízást nem küld."
    )


async def price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        candles = get_candles(5)

        price_value = candles[-1]["close"]

        await update.message.reply_text(
            "📊 BTC/USDT\n\n"
            f"💰 Ár: "
            f"{price_value:,.2f} USDT\n\n"
            "🟢 Kraken adat"
        )

    except Exception as error:
        await update.message.reply_text(
            f"❌ Árlekérési hiba:\n{error}"
        )


async def signal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        result = calculate_signal()

        signal_value = result["signal"]

        if signal_value == "BUY":
            emoji = "🟢"
        elif signal_value == "SELL":
            emoji = "🔴"
        else:
            emoji = "🟡"

        message = (
            "📊 BTC/USDT SIGNAL\n\n"
            f"{emoji} {signal_value}\n\n"
            f"📈 H4 trend: "
            f"{result['trend']}\n\n"
            f"🧠 Indok: "
            f"{result['reason']}\n"
        )

        if signal_value in ("BUY", "SELL"):

            message += (
                "\n"
                f"💰 Belépő: "
                f"{result['entry']:,.2f} USDT\n"
                f"🛑 Stop Loss: "
                f"{result['stop_loss']:,.2f} USDT\n"
                f"🎯 Take Profit: "
                f"{result['take_profit']:,.2f} USDT\n"
                f"📐 R:R = 1:2\n"
                f"📊 ATR: "
                f"{result['atr']:,.2f}\n"
            )

        message += (
            "\n"
            "⏱️ Idősíkok: H4 / M15 / M5\n"
            "🟢 Valós Kraken adat\n"
            "⚠️ Nincs automatikus valódi "
            "megbízás."
        )

        await update.message.reply_text(
            message
        )

    except Exception as error:
        await update.message.reply_text(
            f"❌ Signal hiba:\n{error}"
        )


async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        candles = get_candles(5)

        price_value = candles[-1]["close"]

        await update.message.reply_text(
            "🤖 BOT STATUS\n\n"
            "🟢 Bot: ONLINE\n"
            "🟢 Kraken kapcsolat: OK\n"
            "📊 Piac: BTC/USDT\n"
            "⏱️ Rendszer: H4/M15/M5\n"
            "💰 Aktuális ár: "
            f"{price_value:,.2f} USDT\n\n"
            "⚠️ Trading mód: SIGNAL ONLY"
        )

    except Exception as error:
        await update.message.reply_text(
            f"🔴 Bot hiba:\n{error}"
        )


async def main():
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN nincs beállítva."
        )

    threading.Thread(
        target=start_web_server,
        daemon=True
    ).start()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("price", price)
    )

    app.add_handler(
        CommandHandler("signal", signal)
    )

    app.add_handler(
        CommandHandler("status", status)
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("AI Crypto Bot fut.")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
