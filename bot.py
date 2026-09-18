ticker = next(iter(data["result"].values()))

    price = float(ticker["c"][0])
    open_price = float(ticker["o"])

    return price, open_price


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 AI Crypto Bot elindult!\n\n"
        "📊 Valós Kraken BTC/USDT adatokat használunk.\n"
        "🧪 Jelenleg teszt üzemmód.\n"
        "⚠️ Nincs valódi kereskedés."
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price, open_price = get_kraken_data()

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


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price, open_price = get_kraken_data()

        if price > open_price:
            result = "🟢 BUY"
            reason = "Az ár jelenleg a napi nyitóár felett van."
        elif price < open_price:
            result = "🔴 SELL"
            reason = "Az ár jelenleg a napi nyitóár alatt van."
        else:
            result = "🟡 WAIT"
            reason = "Az ár a napi nyitóár körül van."

        await update.message.reply_text(
            f"📊 BTC/USDT SIGNAL\n\n"
            f"{result}\n\n"
            f"💰 Ár: {price:,.2f} USDT\n"
            f"📌 Napi nyitóár: {open_price:,.2f} USDT\n\n"
            f"ℹ️ {reason}\n\n"
            f"🧪 Teszt jelzés\n"
            f"⚠️ Automatikus valódi ügylet nincs."
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Nem sikerült elkészíteni a jelzést.\n"
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
    app.add_handler(CommandHandler("signal", signal))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("AI Crypto Bot fut.")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())



    
