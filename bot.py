import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 XAU AI Bot elindult!\n\n"
        "A rendszer jelenleg teszt módban működik.\n"
        "Valódi kereskedési megbízást nem küld."
    )

async def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN nincs beállítva.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("Telegram bot fut.")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
