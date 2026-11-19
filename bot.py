import asyncio, json, logging, os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           BotCommand, Message, ReplyKeyboardMarkup, WebAppInfo)
from dotenv import load_dotenv

from game import MuteMW, router as game_router

load_dotenv()
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ["WEBAPP_URL"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

dp = Dispatcher()
dp.message.outer_middleware(MuteMW())
dp.include_router(game_router)


@dp.message(Command("start"), F.chat.type == "private")
async def start(m: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True)
    hint = "\n\nАдмин-панель: /admin" if m.from_user.id == ADMIN_ID else ""
    await m.answer("Привет! Жми кнопку внизу, чтобы открыть магазин 👇" + hint, reply_markup=kb)


@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin(m: Message):
    url = WEBAPP_URL.rstrip("/") + "/admin.html"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Открыть админку", web_app=WebAppInfo(url=url))]])
    await m.answer("Товары и заказы:", reply_markup=kb)


@dp.message(F.web_app_data)
async def order(m: Message):
    try:
        d = json.loads(m.web_app_data.data)
        if d.get("type") != "order":
            return
        lines = [f"• {i['name']} ×{i['qty']} — {i['price'] * i['qty']}" for i in d["items"]]
        text = (f"🧾 Новый заказ №{d['id']}\n\n" + "\n".join(lines) + f"\n\nИтого: {d['sum']} {d.get('cur', '')}\n"
                f"Имя: {d['name']}\nТелефон: {d['phone']}\nАдрес: {d['addr']}\n"
                f"Комментарий: {d.get('note') or '—'}\nОт: @{m.from_user.username or m.from_user.id}")
    except (json.JSONDecodeError, KeyError, TypeError):
        return await m.answer("Не получилось прочитать заказ, попробуй ещё раз.")
    await m.bot.send_message(ADMIN_ID, text)
    await m.answer(f"Заказ №{d['id']} принят ✅ Скоро свяжемся с тобой.")


async def main():
    bot = Bot(BOT_TOKEN)
    await bot.set_my_commands([
        BotCommand(command="roulette", description="Рулетка на XP"),
        BotCommand(command="top", description="Топ стрелков чата"),
        BotCommand(command="xp", description="Мой XP"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
