import html, random, sqlite3, time
from aiogram import F, Router
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.filters import Command
from aiogram.types import (CallbackQuery, InlineKeyboardButton as IB,
                           InlineKeyboardMarkup as IM, Message)

router = Router()
db = sqlite3.connect("game.db")
db.execute("""create table if not exists players(
  chat_id integer, user_id integer, name text,
  balance integer default 0, total integer default 0,
  wins integer default 0, deaths integer default 0,
  mute_until real default 0, primary key(chat_id, user_id))""")
db.commit()

MUTE_SEC, COOLDOWN = 300, 20
games, last = {}, {}   # (chat_id, user_id) -> состояние раунда / время конца

TAKE = ["Нервы стальные, вата осталась живой.", "Вовремя слился, красавчик.", "Жадность фраера сгубила, а ты умнее."]
CLICK = ["Щёлк — пусто!", "Щёлк — мимо!", "Щёлк — живём!"]
DIE = ["вытянул проклятый ствол — дым почернел, а салун замер в тишине.",
       "словил свинец и красиво упал в пыль.", "ушёл в закат без шляпы."]


def who(u):
    return f'<a href="tg://user?id={u.id}">{html.escape(u.full_name)}</a>'


def player(chat, u):
    r = db.execute("select balance,total,wins,deaths from players where chat_id=? and user_id=?", (chat, u.id)).fetchone()
    if not r:
        db.execute("insert into players(chat_id,user_id,name) values(?,?,?)", (chat, u.id, u.full_name))
        r = (0, 0, 0, 0)
    else:
        db.execute("update players set name=? where chat_id=? and user_id=?", (u.full_name, chat, u.id))
    db.commit()
    return r


def apply(chat, uid, d_bal=0, d_tot=0, win=0, death=0, mute=None):
    db.execute("""update players set balance=max(0,balance+?), total=total+?, wins=wins+?, deaths=deaths+?,
                  mute_until=coalesce(?,mute_until) where chat_id=? and user_id=?""",
               (d_bal, d_tot, win, death, mute, chat, uid))
    db.commit()
    return db.execute("select balance,total from players where chat_id=? and user_id=?", (chat, uid)).fetchone()


def is_muted(chat, uid):
    r = db.execute("select mute_until from players where chat_id=? and user_id=?", (chat, uid)).fetchone()
    return bool(r and r[0] > time.time())


class MuteMW(BaseMiddleware):
    """Мягкий мут: пока действует, бот удаляет сообщения игрока (нужны права админа на удаление)."""
    async def __call__(self, handler, event: Message, data):
        if event.chat.type in ("group", "supergroup") and event.from_user and is_muted(event.chat.id, event.from_user.id):
            try:
                await event.delete()
            except Exception:
                pass
            return
        return await handler(event, data)


def kb(uid, pos, pot):
    rows = [[IB(text=f"🎯 Спуск ({pos + 1}/6)", callback_data=f"r:pull:{uid}")]]
    if pot:
        rows.append([IB(text=f"💰 Забрать {pot} XP", callback_data=f"r:take:{uid}")])
    return IM(inline_keyboard=rows)


@router.message(Command("roulette"))
async def roulette(m: Message):
    key = (m.chat.id, m.from_user.id)
    if key in games:
        return await m.reply("Ты уже держишь револьвер. Доиграй раунд кнопками.")
    wait = COOLDOWN - (time.time() - last.get(key, 0))
    if wait > 0:
        return await m.reply(f"Барабан остывает, подожди {int(wait) + 1} сек.")
    player(m.chat.id, m.from_user)
    games[key] = {"bullet": random.randint(1, 6), "pos": 0, "pot": 0}
    await m.answer(f"🔫 {who(m.from_user)} крутит барабан.\nШесть камер, один патрон. Тяни спуск!",
                   reply_markup=kb(m.from_user.id, 0, 0), parse_mode="HTML")


@router.callback_query(F.data.startswith("r:"))
async def play(c: CallbackQuery):
    _, act, uid = c.data.split(":")
    uid = int(uid)
    if c.from_user.id != uid:
        return await c.answer("Это не твой револьвер 🙅", show_alert=True)
    chat, u = c.message.chat.id, c.from_user
    key = (chat, uid)
    g = games.get(key)
    if not g:
        await c.message.edit_reply_markup(reply_markup=None)
        return await c.answer("Раунд уже закончился")

    async def finish(text):
        del games[key]
        last[key] = time.time()
        await c.message.edit_text(text, parse_mode="HTML")
        await c.answer()

    if act == "take":
        if not g["pot"]:
            return await c.answer("Куш пока пуст")
        pot = g["pot"]
        bal, tot = apply(chat, uid, pot, pot, win=1)
        return await finish(f"💰 КУШ ЗАБРАН! (Остановился на {g['pos']}/6)\n\n{who(u)}: {random.choice(TAKE)}\n"
                            f"⚡ Начислено: +{pot} XP (банк: {bal} XP · всего: {tot} XP)")

    g["pos"] += 1
    i = g["pos"]
    if i == g["bullet"]:
        bal0 = player(chat, u)[0]
        penalty = min(bal0, random.randint(15, 40))
        mute = time.time() + MUTE_SEC if c.message.chat.type != "private" else None
        bal, tot = apply(chat, uid, -penalty, 0, death=1, mute=mute)
        head = "💀 ЧЁРНАЯ МЕТКА ШЕРИФА!\nПРОКЛЯТЫЙ ПАТРОН НА 1/6" if i == 1 else f"💥 БАХ! Патрон был на {i}/6"
        text = (f"{head}\n\n{who(u)} {random.choice(DIE)}\n💸 Куш раунда сгорел: {g['pot']} XP.\n"
                f"☠️ Штраф: -{penalty} XP (банк: {bal} XP · всего: {tot} XP)")
        if mute:
            text += "\n🔇 Мягкий мут на 5 мин (сообщения удаляются)."
        return await finish(text)

    g["pot"] += 10 * i
    if i == 5:  # пять камер пусто, шестая точно с патроном
        pay = g["pot"] + 50
        bal, tot = apply(chat, uid, pay, pay, win=1)
        return await finish(f"🏆 ПОЛНЫЙ БАРАБАН!\n\n{who(u)} прошёл пять камер, а в шестой — патрон. Забирает всё.\n"
                            f"⚡ Начислено: +{pay} XP, бонус +50 (банк: {bal} XP · всего: {tot} XP)")
    await c.message.edit_text(f"🔫 {who(u)}\n{random.choice(CLICK)} ({i}/6)\nКуш: {g['pot']} XP. Рискнёшь дальше?",
                              reply_markup=kb(uid, i, g["pot"]), parse_mode="HTML")
    await c.answer()


@router.message(Command("xp"))
async def xp(m: Message):
    b, t, w, d = player(m.chat.id, m.from_user)
    await m.reply(f"{who(m.from_user)}\nБанк: {b} XP · всего: {t} XP\nКушей забрано: {w} · смертей: {d}", parse_mode="HTML")


@router.message(Command("top"))
async def top(m: Message):
    rows = db.execute("select name,total from players where chat_id=? order by total desc limit 10", (m.chat.id,)).fetchall()
    if not rows:
        return await m.reply("Пока никто не играл. Начни с /roulette")
    medals = ["🥇", "🥈", "🥉"]
    lines = [f"{medals[i] if i < 3 else str(i + 1) + '.'} {html.escape(n or '?')} — {t} XP" for i, (n, t) in enumerate(rows)]
    await m.reply("🏆 Топ стрелков чата:\n" + "\n".join(lines), parse_mode="HTML")
