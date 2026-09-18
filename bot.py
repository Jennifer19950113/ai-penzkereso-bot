import os
import json
import threading
import time
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

PREMIUM_FILE = "premium_users.json"
STRIPE_PRICE_ID = "price_1UH2Bc5dT7Ky153dsKxDE1y2"


# =========================
# PREMIUM USERS
# =========================

def load_premium_users():
    try:
        with open(
            PREMIUM_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)
    except Exception:
        return {}


def save_premium_users(users):
    with open(
        PREMIUM_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(users, f)


def is_premium_user(user_id):
    users = load_premium_users()

    expiry = users.get(
        str(user_id)
    )

    if not expiry:
        return False

    return time.time() < expiry


def activate_premium(user_id):
    users = load_premium_users()

    users[str(user_id)] = (
        time.time()
        + (7 * 24 * 60 * 60)
    )

    save_premium_users(users)


# =========================
# WEB SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/success":
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.end_headers()

            self.wfile.write(
                """
                <html>
                <head>
                <meta charset="utf-8">
                <title>AI Pénzkereső</title>
                </head>
                <body>
                <h2>✅ Sikeres fizetés</h2>
                <p>Köszönjük az előfizetést!</p>
                <p>Menj vissza a Telegram botba.</p>
                </body>
                </html>
                """.encode("utf-8")
            )

            return

        if self.path == "/cancel":
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.end_headers()

            self.wfile.write(
                """
                <html>
                <head>
                <meta charset="utf-8">
                <title>AI Pénzkereső</title>
                </head>
                <body>
                <h2>❌ A fizetés megszakítva</h2>
                <p>Visszatérhetsz a Telegram botba.</p>
                </body>
                </html>
                """.encode("utf-8")
            )

            return

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            b"AI Penzkereso Bot OK"
        )

    def do_POST(self):

        if self.path != "/stripe/webhook":
            self.send_response(404)
            self.end_headers()
            return

        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            body = self.rfile.read(
                content_length
            )

            event = json.loads(
                body.decode("utf-8")
            )

            event_type = event.get(
                "type",
                ""
            )

            print(
                "Stripe webhook:",
                event_type
            )

            if event_type == "checkout.session.completed":

                session = (
                    event
                    .get("data", {})
                    .get("object", {})
                )

                telegram_user_id = (
                    session
                    .get("metadata", {})
                    .get("telegram_user_id")
                )

                print(
                    "Sikeres Premium fizetés.",
                    "Telegram user:",
                    telegram_user_id
                )

                if telegram_user_id:

                    activate_premium(
                        telegram_user_id
                    )

                    print(
                        "Premium aktiválva:",
                        telegram_user_id
                    )

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain"
            )
            self.end_headers()

            self.wfile.write(
                b"received"
            )

        except Exception as error:

            print(
                "Stripe webhook error:",
                error
            )

            self.send_response(400)
            self.end_headers()

    def log_message(
        self,
        format,
        *args
    ):
        return


def start_health_server():

    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    server.serve_forever()


# =========================
# KRAKEN
# =========================

def get_candles(interval):

    url = (
        f"{KRAKEN_BASE}"
        f"?pair={PAIR}"
        f"&interval={interval}"
    )

    with urlopen(
        url,
        timeout=15
    ) as response:

        data = json.loads(
            response.read().decode()
        )

    if data.get("error"):
        raise RuntimeError(
            str(data["error"])
        )

    result = data["result"]

    pair_key = next(
        key
        for key in result
        if key != "last"
    )

    candles = result[pair_key]

    return [
        {
            "time": float(c[0]),
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": float(c[6])
        }
        for c in candles
    ]


# =========================
# INDICATORS
# =========================

def ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    value = (
        sum(values[:period])
        / period
    )

    for price in values[period:]:

        value = (
            (price - value)
            * multiplier
            + value
        )

    return value


def rsi(values, period=14):

    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):

        change = (
            values[i]
            - values[i - 1]
        )

        if change >= 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(
                abs(change)
            )

    avg_gain = (
        sum(gains[:period])
        / period
    )

    avg_loss = (
        sum(losses[:period])
        / period
    )

    for i in range(
        period,
        len(gains)
    ):

        avg_gain = (
            (
                avg_gain
                * (period - 1)
            )
            + gains[i]
        ) / period

        avg_loss = (
            (
                avg_loss
                * (period - 1)
            )
            + losses[i]
        ) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (
        100 / (1 + rs)
    )


def atr(candles, period=14):

    if len(candles) < period + 1:
        return None

    true_ranges = []

    for i in range(
        1,
        len(candles)
    ):

        high = candles[i]["high"]
        low = candles[i]["low"]

        previous_close = (
            candles[i - 1]["close"]
        )

        tr = max(
            high - low,
            abs(
                high
                - previous_close
            ),
            abs(
                low
                - previous_close
            )
        )

        true_ranges.append(tr)

    return (
        sum(
            true_ranges[-period:]
        )
        / period
    )


# =========================
# H4 TREND
# =========================

def get_h4_trend():

    candles = get_candles(240)

    closes = [
        c["close"]
        for c in candles
    ]

    ema20 = ema(
        closes,
        20
    )

    ema200 = ema(
        closes,
        200
    )

    current = closes[-1]

    if (
        ema20 is None
        or ema200 is None
    ):
        return "NEUTRAL"

    if (
        current > ema20
        and ema20 > ema200
    ):
        return "BULLISH"

    if (
        current < ema20
        and ema20 < ema200
    ):
        return "BEARISH"

    return "NEUTRAL"


# =========================
# M15 LIQUIDITY SWEEP
# =========================

def get_m15_sweep():

    candles = get_candles(15)

    if len(candles) < 12:
        return "NONE"

    previous = candles[-2]
    current = candles[-1]

    recent = candles[-12:-2]

    recent_low = min(
        c["low"]
        for c in recent
    )

    recent_high = max(
        c["high"]
        for c in recent
    )

    if (
        previous["low"] < recent_low
        and current["close"]
        > previous["high"]
    ):
        return "BUY"

    if (
        previous["high"] > recent_high
        and current["close"]
        < previous["low"]
    ):
        return "SELL"

    return "NONE"


# =========================
# M5 CONFIRMATION
# =========================

def get_m5_confirmation():

    candles = get_candles(5)

    closes = [
        c["close"]
        for c in candles
    ]

    ema20 = ema(
        closes,
        20
    )

    ema50 = ema(
        closes,
        50
    )

    current = closes[-1]

    current_rsi = rsi(
        closes,
        14
    )

    if (
        ema20 is None
        or ema50 is None
        or current_rsi is None
    ):
        return "NONE"

    if (
        current > ema20
        and ema20 > ema50
        and 50 <= current_rsi <= 75
    ):
        return "BUY"

    if (
        current < ema20
        and ema20 < ema50
        and 25 <= current_rsi <= 50
    ):
        return "SELL"

    return "NONE"


# =========================
# TRADE LEVELS
# =========================

def calculate_levels(direction):

    candles = get_candles(5)

    current_price = (
        candles[-1]["close"]
    )

    recent = candles[-5:]

    current_atr = atr(
        candles,
        14
    )

    if current_atr is None:
        current_atr = (
            current_price * 0.002
        )

    if direction == "BUY":

        swing_low = min(
            c["low"]
            for c in recent
        )

        stop_loss = (
            swing_low
            - current_atr * 0.20
        )

        risk = (
            current_price
            - stop_loss
        )

        take_profit = (
            current_price
            + risk * 2
        )

    else:

        swing_high = max(
            c["high"]
            for c in recent
        )

        stop_loss = (
            swing_high
            + current_atr * 0.20
        )

        risk = (
            stop_loss
            - current_price
        )

        take_profit = (
            current_price
            - risk * 2
        )

    return (
        current_price,
        stop_loss,
        take_profit
    )


# =========================
# SIGNAL
# =========================

def calculate_signal():

    h4 = get_h4_trend()
    m15 = get_m15_sweep()
    m5 = get_m5_confirmation()

    if (
        h4 == "BULLISH"
        and m15 == "BUY"
        and m5 == "BUY"
    ):
        direction = "BUY"

    elif (
        h4 == "BEARISH"
        and m15 == "SELL"
        and m5 == "SELL"
    ):
        direction = "SELL"

    else:

        return {
            "signal": "WAIT",
            "h4": h4,
            "m15": m15,
            "m5": m5
        }

    (
        entry,
        stop_loss,
        take_profit
    ) = calculate_levels(
        direction
    )

    return {
        "signal": direction,
        "h4": h4,
        "m15": m15,
        "m5": m5,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit
    }


# =========================
# STRIPE PAYMENT
# =========================

def create_checkout_session(
    telegram_user_id
):

    if not STRIPE_SECRET_KEY:

        raise RuntimeError(
            "STRIPE_SECRET_KEY nincs "
            "beállítva a Renderben."
        )

    data = {

        "mode":
            "subscription",

        "success_url":
            "https://ai-penzkereso-bot.onrender.com/success",

        "cancel_url":
            "https://ai-penzkereso-bot.onrender.com/cancel",

        "line_items[0][price]":
            STRIPE_PRICE_ID,

        "line_items[0][quantity]":
            "1",

        "billing_address_collection":
            "auto",

        "payment_method_collection":
            "always",

        "allow_promotion_codes":
            "true",

        "metadata[telegram_user_id]":
            str(telegram_user_id),

        "subscription_data[metadata][telegram_user_id]":
            str(telegram_user_id)
    }

    body = urllib.parse.urlencode(
        data
    ).encode()

    request = Request(

        "https://api.stripe.com/"
        "v1/checkout/sessions",

        data=body,

        headers={
            "Authorization":
                "Bearer "
                + STRIPE_SECRET_KEY,

            "Content-Type":
                "application/"
                "x-www-form-urlencoded"
        },

        method="POST"
    )

    try:

        with urlopen(
            request,
            timeout=20
        ) as response:

            result = json.loads(
                response
                .read()
                .decode()
            )

    except Exception as error:

        if hasattr(
            error,
            "read"
        ):

            stripe_error = (
                error
                .read()
                .decode()
            )

            raise RuntimeError(
                stripe_error
            )

        raise

    if "url" not in result:

        raise RuntimeError(
            str(result)
        )

    return result["url"]


# =========================
# TELEGRAM /START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🤖 AI Pénzkereső Bot\n\n"

        "📊 BTC/USDT\n\n"

        "H4 → fő trend\n"
        "M15 → liquidity sweep\n"
        "M5 → belépési megerősítés\n\n"

        "🛑 Strukturális Stop Loss\n"
        "🎯 Take Profit: R:R 1:2\n\n"

        "⚠️ Jelző mód – valódi "
        "megbízást nem küld.\n\n"

        "💎 Premium: /premium"
    )


# =========================
# PREMIUM
# =========================

async def premium(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        checkout_url = (
            create_checkout_session(
                update.effective_user.id
            )
        )

        await update.message.reply_text(

            "💎 AI Pénzkereső Premium\n\n"

            "📊 BTC/USDT "
            "H4/M15/M5 piaci elemzések\n\n"

            "💰 Előfizetés: €60 / hét\n\n"

            "👇 Fizetés Stripe-on:\n\n"

            f"{checkout_url}"
        )

    except Exception as error:

        await update.message.reply_text(

            "❌ A fizetési oldal "
            "létrehozása nem sikerült.\n\n"

            f"Hiba:\n{error}"
        )


# =========================
# PRICE
# =========================

async def price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        candles = get_candles(5)

        current_price = (
            candles[-1]["close"]
        )

        await update.message.reply_text(

            "📈 BTC/USDT\n\n"
            f"💰 Aktuális ár: "
            f"{current_price:.2f}"
        )

    except Exception as error:

        await update.message.reply_text(

            "❌ Nem sikerült lekérni az árat.\n\n"
            f"Hiba: {error}"
        )


# =========================
# SIGNAL
# =========================

async def signal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        result = calculate_signal()

        if result["signal"] == "WAIT":

            await update.message.reply_text(

                "⏳ Jelenleg nincs megfelelő jel.\n\n"

                f"H4: {result['h4']}\n"
                f"M15: {result['m15']}\n"
                f"M5: {result['m5']}"
            )

            return

        await update.message.reply_text(

            "🚨 BTC/USDT SIGNAL\n\n"

            f"📌 Irány: "
            f"{result['signal']}\n"

            f"💰 Belépő: "
            f"{result['entry']:.2f}\n"

            f"🛑 Stop Loss: "
            f"{result['stop_loss']:.2f}\n"

            f"🎯 Take Profit: "
            f"{result['take_profit']:.2f}\n\n"

            f"H4: {result['h4']}\n"
            f"M15: {result['m15']}\n"
            f"M5: {result['m5']}\n\n"

            "⚠️ Ez jelzés, nem automatikus megbízás."
        )

    except Exception as error:

        await update.message.reply_text(

            "❌ A jelzés lekérése nem sikerült.\n\n"
            f"Hiba: {error}"
        )


# =========================
# STATUS
# =========================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🤖 AI Pénzkereső Bot\n\n"

        "🟢 Állapot: online\n"
        "📊 Piac: BTC/USDT\n"
        "⏱ Idősíkok: H4 / M15 / M5\n"
        "💎 Premium: /premium\n"
        "📈 Ár: /price\n"
        "🚨 Jelzés: /signal"
    )


# =========================
# MAIN
# =========================

def main():

    threading.Thread(
        target=start_health_server,
        daemon=True
    ).start()

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "premium",
            premium
        )
    )

    application.add_handler(
        CommandHandler(
            "price",
            price
        )
    )

    application.add_handler(
        CommandHandler(
            "signal",
            signal
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status
        )
    )

    print(
        "AI Pénzkereső Bot elindult."
    )

    application.run_polling()


if __name__ == "__main__":
    main()
