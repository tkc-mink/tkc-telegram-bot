import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from config.tokens import BOT_TOKENS
from bots import tkc_autoplus, giant_willow, tkc_prime_tyre, texpress_advance

async def start_bot(name, token, handler):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", handler))
    await app.initialize()
    await app.start()
    print(f"{name} started.")
    return app

async def main():
    bots = [
        start_bot("shiba_tkc", BOT_TOKENS["shiba_tkc"], tkc_autoplus.handle),
        start_bot("giantjiew", BOT_TOKENS["giantjiew"], giant_willow.handle),
        start_bot("p_tyretkc", BOT_TOKENS["p_tyretkc"], tkc_prime_tyre.handle),
        start_bot("speedtkc", BOT_TOKENS["speedtkc"], texpress_advance.handle),
    ]
    apps = await asyncio.gather(*bots)
    await asyncio.Event().wait()  # Keep running

if __name__ == "__main__":
    asyncio.run(main())
