import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", "10000"))


# Render számára szükséges webes port
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"AI Penkereso Bot is running.")

    def log_message(self, format, *args):
        return


def start_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 XAU AI Bot elindult!\n\n"
        "A rendszer jelenleg teszt módban működik.\n"
        "Valódi kereskedési megbízást nem küld."
    )


async def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN nincs beállítva.")

    # Render port elindítása
    threading.Thread(target=start_web_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("Telegram bot fut.")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

