import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

@dp.message()
async def my_handler(message: Message):
    print(message.chat.id)


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

