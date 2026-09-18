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


def get_kraken_price():
    url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSDT"

    with urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("error"):
        raise RuntimeError(str(data["error"]))

    ticker = data["result"]["XBTUSDT"]
    price = float(ticker["c"][0])

    return price


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 AI Crypto Bot elindult!\n\n"
        "📊 Valós Kraken piaci adatokat használunk.\n"
        "💰 Jelenleg csak tesztelünk.\n"
        "⚠️ Nincs valódi kereskedés és nincs befizetés."
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = get_kraken_price()

        await update.message.reply_text(
            f"📊 Kraken BTC/USDT\n\n"
            f"💰 Aktuális ár: {price:,.2f} USDT\n\n"
            f"🟢 Valós piaci adat\n"
            f"🧪 Teszt üzemmód\n"
            f"⚠️ Valódi kereskedés még nincs."
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Nem sikerült lekérni a Kraken árát.\n"
            f"Hiba: {e}"
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

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("AI Crypto Bot fut.")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
