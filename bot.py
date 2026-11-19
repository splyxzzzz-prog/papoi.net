import asyncio
import json
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]

dp = Dispatcher()

REACTIONS = [
    "Это шедевр, не спорю 🗿",
    "Вселенная одобряет 🌌",
    "Ну и бред. Мне нравится 🤌",
    "Записал в архив великой хуйни 📜",
    "Ты это сам придумал? Гений 🧠",
    "Бабушка бы одобрила 👵",
]


def keyboard() -> ReplyKeyboardMarkup:
    # sendData() в мини-аппе работает ТОЛЬКО с кнопкой из обычной (reply) клавиатуры
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎰 Открыть автомат хуйни", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="🎲 Рандом прямо тут")],
        ],
        resize_keyboard=True,
    )


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Привет. Я бот, который генерирует рандомную хуйню.\n"
        "Жми кнопку внизу — откроется мини-апп 👇",
        reply_markup=keyboard(),
    )


@dp.message(F.text == "🎲 Рандом прямо тут")
async def quick_random(message: Message):
    number = random.randint(1, 10**6)
    await message.answer(f"Твоё число: {number}\nБесполезно, зато честно.")


@dp.message(F.web_app_data)
async def from_webapp(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        text = str(data.get("text", ""))[:500]
    except (json.JSONDecodeError, AttributeError):
        text = message.web_app_data.data[:500]

    await message.answer(f"Из мини-аппа прилетело:\n\n«{text}»\n\n{random.choice(REACTIONS)}")


async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
