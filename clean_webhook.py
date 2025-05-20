import asyncio
from aiogram import Bot

async def main():
    bot = Bot(token="8188396381:AAE3VpGVs8a4gDkcrDqQTia9fe_DFh3LSo0")
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deleted")

if __name__ == "__main__":
    asyncio.run(main())
